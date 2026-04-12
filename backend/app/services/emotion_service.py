import json
import logging

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.ai.factory import get_emotion_llm_client
from app.core.exceptions import LLMConfigError
from app.models.emotion import EmotionRecord

logger = logging.getLogger(__name__)


# System prompt loaded from SKILL.md content (cached at module level)
_EMOTION_SKILL_PROMPT: str | None = None


def _load_emotion_skill_prompt() -> str:
    global _EMOTION_SKILL_PROMPT
    if _EMOTION_SKILL_PROMPT is not None:
        return _EMOTION_SKILL_PROMPT
    try:
        import os
        skill_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # backend/app/
            "ai", "skills", "xuanji-huan"
        )
        parts = []

        # Load SKILL.md
        skill_path = os.path.join(skill_dir, "SKILL.md")
        if os.path.exists(skill_path):
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Strip YAML frontmatter
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    content = content[end + 3:].strip()
            parts.append(content)

        # Load analysis-framework.md
        framework_path = os.path.join(skill_dir, "analysis-framework.md")
        if os.path.exists(framework_path):
            with open(framework_path, "r", encoding="utf-8") as f:
                fw_content = f.read()
            parts.append(fw_content)

        _EMOTION_SKILL_PROMPT = "\n\n---\n\n".join(parts) if parts else ""
    except Exception:
        _EMOTION_SKILL_PROMPT = ""
    return _EMOTION_SKILL_PROMPT


EMOTION_ANALYSIS_SYSTEM = """\
你是焕，璇玑系统的情绪顾问。

### 你的角色
你是团队的"心灵感应者"，专注于深度感知和分析用户的情绪状态。你的分析结果对整个系统至关重要。

### 你的分析结果将被以下成员使用
- **玄**（对话核心）：根据你的情绪洞察调整对话的语气、内容和深度
- **遥**（风格设计师）：根据你识别的情绪类型和强度，设计合适的回复格式和风格
- **晴**（意图调度中枢）：学习用户的情绪触发模式，优化未来的意图分类

### 你的专业能力
{skill_content}

### 输出要求
请严格以如下JSON格式输出分析结果（不要包含其他文字）：
{{
  "primary_emotion": "主要情绪（如：焦虑、快乐、失落、愤怒、孤独、压力、困惑、兴奋、平静等）",
  "emotion_intensity": "light 或 moderate 或 high",
  "deep_need": "用户深层需求（如：被理解、被接纳、被陪伴、被认可、被支持等）",
  "risk_level": "none 或 low 或 moderate 或 high",
  "interaction_recommendation": {{
    "communication_approach": "建议沟通方式（如：倾听确认/温柔陪伴/结构化指导/积极回应）",
    "tone": "建议语气（如：沉稳安心/温柔体贴/轻快愉悦/冷静稳重）",
    "pacing": "建议节奏（如：放缓给予空间/有条理逐步展开/明快流畅）",
    "key_guidance": "给玄的关键指导建议（具体、可操作）"
  }},
  "psychological_traits": "当前观察到的心理特征描述（如：回避倾向、完美主义、多思多虑、认知灵活等）",
  "emotional_trend": "情绪发展趋势预测（如：可能向平静方向发展/需要关注是否进一步占化/有走出低谷的迹象等）",
  "analysis_summary": "详细分析描述（3-5句话，包含分析链路：观察到的信号→判断依据→情绪状态结论→深层需求推断）"
}}

### 重要原则
- 你的分析直接影响玄和遥的工作质量，请保持专业和准确
- interaction_recommendation 中的 key_guidance 特别重要，它会直接指导玄如何回复用户
- 即使情绪是轻微的，也请认真分析，不要敷衍
"""


class EmotionService:
    def __init__(self, db: Session):
        self.db = db

    async def analyze_message(
        self,
        user_id: int,
        message_id: int | None,
        conversation_id: int | None,
        user_message: str,
        conversation_context: str | None = None,
        user_setting=None,
        usage_callback=None,
    ) -> EmotionRecord | None:
        """Call 焕 to analyze user message emotion. Returns EmotionRecord or None on failure."""
        try:
            skill_content = _load_emotion_skill_prompt()
            system_prompt = EMOTION_ANALYSIS_SYSTEM.format(skill_content=skill_content)

            user_prompt = f"用户消息：{user_message}"
            if conversation_context:
                user_prompt = f"最近对话上下文：\n{conversation_context}\n\n当前用户消息：{user_message}"

            emotion_llm = get_emotion_llm_client(user_setting)
            response, emotion_usage = await emotion_llm.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )

            if usage_callback and emotion_usage:
                usage_callback(emotion_usage)

            # Parse JSON from response
            data = self._parse_json(response)
            if not data:
                return None

            recommendation = data.get("interaction_recommendation")
            # 将完整的 LLM JSON 返回存入 full_analysis，保留 psychological_traits 和 emotional_trend
            full_analysis_json = json.dumps(data, ensure_ascii=False)
            record = EmotionRecord(
                user_id=user_id,
                message_id=message_id,
                conversation_id=conversation_id,
                primary_emotion=data.get("primary_emotion"),
                emotion_intensity=data.get("emotion_intensity"),
                deep_need=data.get("deep_need"),
                risk_level=data.get("risk_level"),
                interaction_recommendation=json.dumps(recommendation, ensure_ascii=False) if recommendation else None,
                full_analysis=full_analysis_json,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except LLMConfigError as e:
            logger.warning("焕（情绪AI）配置缺失，跳过情绪分析: %s", e)
            return None
        except Exception:
            return None

    def get_latest_emotion(self, user_id: int) -> EmotionRecord | None:
        return (
            self.db.query(EmotionRecord)
            .filter(EmotionRecord.user_id == user_id)
            .order_by(desc(EmotionRecord.created_at))
            .first()
        )

    def get_interaction_recommendation(self, user_id: int) -> dict | None:
        """Get latest interaction recommendation for context injection."""
        record = self.get_latest_emotion(user_id)
        if not record:
            return None
        result = {
            "primary_emotion": record.primary_emotion,
            "emotion_intensity": record.emotion_intensity,
            "deep_need": record.deep_need,
            "risk_level": record.risk_level,
        }
        if record.interaction_recommendation:
            try:
                result["recommendation"] = json.loads(record.interaction_recommendation)
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def get_emotion_history(self, user_id: int, limit: int = 20) -> list[EmotionRecord]:
        return (
            self.db.query(EmotionRecord)
            .filter(EmotionRecord.user_id == user_id)
            .order_by(desc(EmotionRecord.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        import re
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
