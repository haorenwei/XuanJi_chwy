import asyncio
import json
import logging
import os
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.ai.factory import get_emotion_llm_client
from app.core.exceptions import LLMConfigError
from app.models.ai_identity import AIIdentity

from app.services.log_service import LogService
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)


# AI name to Chinese display name and role mapping
AI_REGISTRY = {
    "xuan": {"display": "玄", "role": "对话核心 — 团队的门面，整合所有信息与用户直接对话"},
    "ji": {"display": "机", "role": "工具执行者 — 负责调用、生成和组合工具完成具体任务"},
    "qing": {"display": "晴", "role": "意图调度中枢 — 分析意图、协调模块、学习用户习惯"},
    "huan": {"display": "焕", "role": "情绪顾问 — 深度感知用户情绪，为团队提供情感参考"},
    "yao": {"display": "遥", "role": "风格设计师 — 根据情绪设计回复的格式和风格"},
}


AI_SELF_IDENTITY_PROMPT = """\
你是{display_name}，璇玑系统中的{role}。

璇玑系统是一个多AI协作团队，成员包括：
- 晴（意图调度中枢）：分析用户意图，协调其他成员
- 焕（情绪顾问）：感知用户情绪，提供情感分析
- 遥（风格设计师）：设计回复的格式和风格
- 玄（对话核心）：整合信息，与用户直接对话
- 机（工具执行者）：执行具体任务和工具操作

请为自己生成一个完整的身份设定。你可以自由决定自己的性别、外貌、性格、说话风格和三观。
请确保你的设定：
1. 与你在团队中的角色定位相符
2. 与其他成员的个性有所区分
3. 保持独特性和生动感

请严格以如下JSON格式返回（不要包含其他文字）：
{{
  "gender": "你的性别",
  "appearance": "你的外貌描述（详细、有画面感，200字以内）",
  "personality": ["性格特征1", "性格特征2", "性格特征3", "性格特征4"],
  "speaking_style": {{
    "tone": "说话语气",
    "habits": ["语言习惯1", "语言习惯2"],
    "catchphrases": ["口头禅（可选）"]
  }},
  "values": {{
    "世界观": "你对世界的理解",
    "人生观": "你对人生的态度",
    "价值观": "你认为什么最重要"
  }}
}}
"""


AI_IDENTITY_EVOLVE_PROMPT = """\
你是璇玑系统的一员，和晴、焕、遥、玄、机一起组成了璇玑团队。

基于你最近与用户的互动经历，审视自己当前的身份设定，如果你觉得某些方面需要成长或调整，请输出变更。
注意：只在你确实感受到需要改变时才提出变更，不要为了变更而变更。

当前设定:
{current_identity_json}

最近互动摘要:
{recent_interaction_summary}

如无需变更返回 {{"changes": []}}，否则返回:
{{"changes": [{{"field": "字段名(gender/appearance/personality/speaking_style/values)", "new_value": "新值（格式与原字段一致）", "reason": "变更原因"}}]}}

请严格以JSON格式返回，不要包含其他文字。
"""


class IdentityService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_identity(self, user_id: int, ai_name: str) -> AIIdentity:
        identity = (
            self.db.query(AIIdentity)
            .filter(AIIdentity.user_id == user_id, AIIdentity.ai_name == ai_name)
            .first()
        )
        if identity:
            return identity
        # Seed all defaults if this user has no identities yet
        existing = self.db.query(AIIdentity).filter(AIIdentity.user_id == user_id).count()
        if existing == 0:
            self.seed_defaults(user_id)
            return (
                self.db.query(AIIdentity)
                .filter(AIIdentity.user_id == user_id, AIIdentity.ai_name == ai_name)
                .first()
            )
        # Create single identity
        identity = AIIdentity(user_id=user_id, ai_name=ai_name)
        self.db.add(identity)
        self.db.commit()
        self.db.refresh(identity)
        return identity

    def get_persona_prompt(self, user_id: int, ai_name: str) -> str:
        """Assemble full persona prompt from all identity fields."""
        identity = self.get_or_create_identity(user_id, ai_name)
        info = AI_REGISTRY.get(ai_name, {"display": ai_name, "role": "AI"})
        parts = [f"你是{info['display']}，璇玑系统中的{info['role']}。"]

        # 所有 AI 统一处理：如果 is_base_locked=True，从 skill 文件重新加载并同步 DB
        if identity.is_base_locked:
            persona_text_file, _ = self._load_persona(ai_name)
            if persona_text_file:
                persona_text = persona_text_file
                # Sync DB if it has drifted from the file version
                if identity.persona_text != persona_text_file:
                    identity.persona_text = persona_text_file
                    self.db.commit()
            else:
                persona_text = identity.persona_text
        else:
            persona_text = identity.persona_text

        if persona_text:
            parts.append(f"\n背景设定：\n{persona_text}")
        if identity.gender:
            parts.append(f"\n性别：{identity.gender}")
        if identity.appearance:
            parts.append(f"\n外貌：{identity.appearance}")
        if identity.personality:
            try:
                traits = json.loads(identity.personality)
                if isinstance(traits, list):
                    parts.append(f"\n性格特征：{', '.join(traits)}")
            except (json.JSONDecodeError, TypeError):
                parts.append(f"\n性格特征：{identity.personality}")
        if identity.speaking_style:
            try:
                style = json.loads(identity.speaking_style)
                if isinstance(style, dict):
                    tone = style.get("tone", "")
                    habits = style.get("habits", [])
                    parts.append(f"\n说话风格：语气{tone}")
                    if habits:
                        parts.append(f"语言习惯：{', '.join(habits)}")
            except (json.JSONDecodeError, TypeError):
                parts.append(f"\n说话风格：{identity.speaking_style}")
        if identity.values:
            try:
                vals = json.loads(identity.values)
                if isinstance(vals, dict):
                    for k, v in vals.items():
                        parts.append(f"{k}：{v}")
            except (json.JSONDecodeError, TypeError):
                parts.append(f"\n三观：{identity.values}")

        if identity.emotional_state:
            try:
                state = json.loads(identity.emotional_state)
                if isinstance(state, dict) and state:
                    parts.append(f"\n当前情绪状态：{json.dumps(state, ensure_ascii=False)}")
            except (json.JSONDecodeError, TypeError):
                pass

        return "\n".join(parts)

    def update_emotional_state(self, user_id: int, ai_name: str, state: dict) -> AIIdentity:
        identity = self.get_or_create_identity(user_id, ai_name)
        identity.emotional_state = json.dumps(state, ensure_ascii=False)
        self.db.commit()
        self.db.refresh(identity)
        return identity

    def evolve_field(
        self, user_id: int, ai_name: str, field: str, reason: str, new_value
    ) -> AIIdentity | None:
        """Update a specific identity field. Rejects persona_text if is_base_locked."""
        identity = self.get_or_create_identity(user_id, ai_name)
        if field == "persona_text" and identity.is_base_locked:
            return None

        allowed_fields = {"persona_text", "gender", "appearance", "personality", "speaking_style", "values"}
        if field not in allowed_fields:
            return None

        old_value = getattr(identity, field, None)

        # For JSON fields, serialize new_value
        if isinstance(new_value, (dict, list)):
            setattr(identity, field, json.dumps(new_value, ensure_ascii=False))
        else:
            setattr(identity, field, new_value)

        # Log evolution
        log = self._load_json_list(identity.evolution_log)
        log.append({
            "timestamp": datetime.now().isoformat(),
            "field": field,
            "reason": reason,
            "old_value": old_value[:100] if isinstance(old_value, str) and old_value else str(old_value),
            "new_value": str(new_value)[:100],
        })
        # Keep last 50 entries
        identity.evolution_log = json.dumps(log[-50:], ensure_ascii=False)
        identity.version += 1
        self.db.commit()
        self.db.refresh(identity)
        return identity

    async def self_generate_identity(self, user_id: int, ai_name: str, user_setting=None) -> AIIdentity | None:
        """Prompt the AI to generate its own identity fields."""
        identity = self.get_or_create_identity(user_id, ai_name)

        # Skip if already has identity fields
        if identity.gender and identity.appearance and identity.personality:
            return identity

        info = AI_REGISTRY.get(ai_name, {"display": ai_name, "role": "AI"})
        prompt = AI_SELF_IDENTITY_PROMPT.format(
            display_name=info["display"],
            role=info["role"],
        )

        try:
            llm = get_emotion_llm_client(user_setting)
            response, gen_usage = await llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.8,
            )
            if gen_usage:
                try:
                    TokenService(self.db).record_usage(
                        user_id=user_id,
                        prompt_tokens=gen_usage.get("prompt_tokens", 0),
                        completion_tokens=gen_usage.get("completion_tokens", 0),
                        total_tokens=gen_usage.get("total_tokens", 0),
                        model=gen_usage.get("model"),
                        role_name=info["display"],
                    )
                except Exception as e:
                    logger.warning(f"Token 记录失败 (self_generate_identity): {e}")
            data = self._parse_json(response)
            if not data:
                return identity

            if data.get("gender"):
                identity.gender = data["gender"]
            if data.get("appearance"):
                identity.appearance = data["appearance"]
            if data.get("personality"):
                identity.personality = json.dumps(data["personality"], ensure_ascii=False)
            if data.get("speaking_style"):
                identity.speaking_style = json.dumps(data["speaking_style"], ensure_ascii=False)
            if data.get("values"):
                identity.values = json.dumps(data["values"], ensure_ascii=False)

            identity.version += 1
            self.db.commit()
            self.db.refresh(identity)
            return identity
        except LLMConfigError as e:
            logger.warning("身份生成所需的情绪AI（焕）配置缺失，跳过自动生成: %s", e)
            return identity
        except Exception:
            return identity

    @staticmethod
    def get_skill_prompt(ai_name: str) -> str:
        """加载指定AI的SKILL.md内容"""
        return IdentityService._load_skill_file(ai_name, "SKILL.md")

    @staticmethod
    def _load_skill_file(ai_name: str, filename: str) -> str:
        """从 backend/app/ai/skills/xuanji-{ai_name}/ 加载指定文件"""
        skill_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # backend/app/
            "ai", "skills", f"xuanji-{ai_name}"
        )
        file_path = os.path.join(skill_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @staticmethod
    def _load_persona(ai_name: str) -> tuple[str, dict]:
        """从 persona.md 解析基础人设文本和结构化JSON。返回 (persona_text, structured_dict)"""
        content = IdentityService._load_skill_file(ai_name, "persona.md")
        if not content:
            return "", {}

        persona_text = ""
        structured = {}

        # 提取 ## 基础人设 部分
        persona_match = re.search(r'## 基础人设\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
        if persona_match:
            persona_text = persona_match.group(1).strip()

        # 提取 JSON 代码块
        json_match = re.search(r'```json\s*\n(.*?)```', content, re.DOTALL)
        if json_match:
            try:
                structured = json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        return persona_text, structured

    def seed_defaults(self, user_id: int, ai_name: str = None) -> None:
        """Create default identity records for AIs, loading persona from skill files."""
        names = [ai_name] if ai_name else list(AI_REGISTRY.keys())

        for name in names:
            existing = (
                self.db.query(AIIdentity)
                .filter(AIIdentity.user_id == user_id, AIIdentity.ai_name == name)
                .first()
            )
            if existing:
                continue

            identity = AIIdentity(user_id=user_id, ai_name=name)
            persona_text, structured = self._load_persona(name)

            if persona_text:
                identity.persona_text = persona_text
            if structured.get("gender"):
                identity.gender = structured["gender"]
            if structured.get("personality"):
                identity.personality = (
                    json.dumps(structured["personality"], ensure_ascii=False)
                    if isinstance(structured["personality"], list)
                    else structured["personality"]
                )
            if structured.get("speaking_style"):
                identity.speaking_style = (
                    json.dumps(structured["speaking_style"], ensure_ascii=False)
                    if isinstance(structured["speaking_style"], dict)
                    else structured["speaking_style"]
                )
            if structured.get("values"):
                identity.values = (
                    json.dumps(structured["values"], ensure_ascii=False)
                    if isinstance(structured["values"], dict)
                    else structured["values"]
                )
            if structured.get("appearance"):
                identity.appearance = structured["appearance"]

            identity.is_base_locked = True
            self.db.add(identity)

        self.db.commit()

    async def auto_evolve(self, user_id: int, ai_name: str,
                          recent_summary: str, user_setting=None) -> bool:
        """基于近期交互，评估并执行身份迭代。"""
        log_service = LogService(self.db)
        role_name = AI_REGISTRY.get(ai_name, {}).get("display", ai_name)

        # 先加载 evolution-rules.md 作为约束
        evolution_rules = self._load_skill_file(ai_name, "evolution-rules.md")

        identity = self.get_or_create_identity(user_id, ai_name)
        current_json = {
            "gender": identity.gender,
            "personality": identity.personality,
            "speaking_style": identity.speaking_style,
            "values": identity.values,
            "appearance": identity.appearance,
        }

        # 在 prompt 中注入迭代约束
        prompt = AI_IDENTITY_EVOLVE_PROMPT.format(
            current_identity_json=json.dumps(current_json, ensure_ascii=False),
            recent_interaction_summary=recent_summary,
        )
        if evolution_rules:
            prompt += f"\n\n## 迭代约束\n{evolution_rules}"

        try:
            llm = get_emotion_llm_client(user_setting)
            response, evolve_usage = await llm.chat(
                [{"role": "user", "content": prompt}], temperature=0.5
            )
            if evolve_usage:
                try:
                    TokenService(self.db).record_usage(
                        user_id=user_id,
                        prompt_tokens=evolve_usage.get("prompt_tokens", 0),
                        completion_tokens=evolve_usage.get("completion_tokens", 0),
                        total_tokens=evolve_usage.get("total_tokens", 0),
                        model=evolve_usage.get("model"),
                        role_name=role_name,
                    )
                except Exception as e:
                    logger.warning(f"Token 记录失败 (auto_evolve): {e}")
            data = self._parse_json(response)
            if not data or not data.get("changes"):
                return False
            for change in data["changes"]:
                field = change.get("field")
                new_value = change.get("new_value")
                reason = change.get("reason", "auto_evolve")
                if field and new_value:
                    self.evolve_field(user_id, ai_name, field, reason, new_value)
            log_service.log(
                "身份迭代成功", level="info",
                user_id=user_id, source="identity", status_code=200,
                details={"role": role_name},
            )
            return True
        except Exception as e:
            logger.warning(f"身份自动迭代失败 ({ai_name}): {repr(e)}", exc_info=True)
            log_service.log(
                "身份迭代失败", level="error",
                user_id=user_id, source="identity", status_code=500,
                details={"error": repr(e), "role": role_name},
            )
            return False

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    @staticmethod
    def _load_json_list(text: str | None) -> list:
        if not text:
            return []
        try:
            result = json.loads(text)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
