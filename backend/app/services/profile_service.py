import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)


class ProfileService:
    PERSONAL_INFO_KEYWORDS = [
        "我叫", "我的名字", "叫我", "我是", "我姓", "我今年",
        "我喜欢", "我爱", "我的爱好", "我住在", "我在",
        "我的工作", "我做", "我的职业", "我的生日", "我属",
        "我的性别", "我是男", "我是女", "我的年龄",
        "你可以叫我", "请叫我", "称呼我",
    ]

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_profile(self, user_id: int) -> UserProfile:
        profile = (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )
        if profile:
            return profile
        profile = UserProfile(user_id=user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_from_emotion(self, user_id: int, emotion_data: dict) -> UserProfile:
        """Incrementally update user profile based on new emotion analysis."""
        profile = self.get_or_create_profile(user_id)

        # Update core needs if identified
        deep_need = emotion_data.get("deep_need")
        if deep_need:
            existing = self._load_json_list(profile.core_needs)
            if deep_need not in existing:
                existing.append(deep_need)
                # Keep only recent 10 unique needs
                profile.core_needs = json.dumps(existing[-10:], ensure_ascii=False)

        # Update trigger topics from high-emotion events
        if emotion_data.get("emotion_intensity") == "high":
            primary = emotion_data.get("primary_emotion", "")
            triggers = self._load_json_list(profile.trigger_topics)
            if primary and primary not in triggers:
                triggers.append(primary)
                profile.trigger_topics = json.dumps(triggers[-10:], ensure_ascii=False)

        # Update safe topics from light-emotion events
        if emotion_data.get("emotion_intensity") == "light":
            safe = self._load_json_list(profile.safe_topics)
            topic = emotion_data.get("primary_emotion", "")
            if topic and topic not in safe:
                safe.append(topic)
                profile.safe_topics = json.dumps(safe[-10:], ensure_ascii=False)

        # 从 full_analysis 提取性格特征
        full_analysis = emotion_data.get("full_analysis")
        if full_analysis:
            try:
                analysis_data = json.loads(full_analysis) if isinstance(full_analysis, str) else full_analysis
                psych_traits = analysis_data.get("psychological_traits", [])
                if psych_traits:
                    existing_traits = self._load_json_list(profile.personality_traits)
                    for trait in psych_traits[:3]:  # 每次最多3个
                        if isinstance(trait, str) and 2 <= len(trait) <= 6 and trait not in existing_traits:
                            existing_traits.append(trait)
                    profile.personality_traits = json.dumps(existing_traits[-15:], ensure_ascii=False)
            except (json.JSONDecodeError, AttributeError):
                pass

        # Update emotional baseline
        baseline = self._load_json_dict(profile.emotional_baseline)
        emotion = emotion_data.get("primary_emotion", "unknown")
        baseline[emotion] = baseline.get(emotion, 0) + 1
        profile.emotional_baseline = json.dumps(baseline, ensure_ascii=False)

        # 推断依恋风格
        style = self._infer_attachment_style(baseline)
        if style:
            profile.attachment_style = style

        profile.version += 1
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_profile_context(self, user_id: int) -> str:
        """Generate human-readable profile summary for prompt injection."""
        profile = (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )
        if not profile:
            return ""

        parts = []
        if profile.summary_text:
            parts.append(f"用户画像: {profile.summary_text}")
        if profile.core_needs:
            needs = self._load_json_list(profile.core_needs)
            if needs:
                parts.append(f"核心需求: {', '.join(needs)}")
        if profile.personality_traits:
            traits = self._load_json_list(profile.personality_traits)
            if traits:
                parts.append(f"性格特征: {', '.join(traits)}")
        if profile.interests:
            interests = self._load_json_list(profile.interests)
            if interests:
                parts.append(f"兴趣爱好: {', '.join(interests)}")
        if profile.attachment_style:
            parts.append(f"依恋模式: {profile.attachment_style}")
        if profile.emotional_baseline:
            baseline = self._load_json_dict(profile.emotional_baseline)
            if baseline:
                top = sorted(baseline.items(), key=lambda x: x[1], reverse=True)[:3]
                parts.append(f"情绪基线: {', '.join(f'{k}({v})' for k, v in top)}")

        return "\n".join(parts) if parts else ""

    def update_summary(self, user_id: int, summary: str) -> UserProfile:
        profile = self.get_or_create_profile(user_id)
        profile.summary_text = summary
        profile.version += 1
        self.db.commit()
        self.db.refresh(profile)
        return profile

    async def generate_summary(self, user_id: int, user_setting=None):
        """定期汇总用户画像为自然语言摘要"""
        profile = self.get_or_create_profile(user_id)

        # 收集所有非空字段
        fields = {}
        if profile.personality_traits:
            fields["性格特征"] = profile.personality_traits
        if profile.interests:
            fields["兴趣爱好"] = profile.interests
        if profile.core_needs:
            fields["核心需求"] = profile.core_needs
        if profile.attachment_style:
            fields["依恋风格"] = profile.attachment_style
        if profile.trigger_topics:
            fields["敏感话题"] = profile.trigger_topics
        if profile.safe_topics:
            fields["安全话题"] = profile.safe_topics
        if profile.emotional_baseline:
            fields["情绪基线"] = profile.emotional_baseline

        if not fields:
            return

        prompt = f"""基于以下用户画像数据，生成一段100字以内的综合画像摘要，用自然语言描述这个用户的特点。

用户画像数据：
{json.dumps(fields, ensure_ascii=False, indent=2)}

要求：
- 100字以内
- 自然语言，不要列表
- 描述用户的性格、兴趣、情绪特点
- 直接输出摘要文本，不要任何前缀"""

        try:
            from app.ai.factory import get_emotion_llm_client
            llm = get_emotion_llm_client(user_setting)
            response, summary_usage = await llm.chat(
                [{"role": "user", "content": prompt}], temperature=0.5
            )
            if summary_usage:
                try:
                    TokenService(self.db).record_usage(
                        user_id=user_id,
                        prompt_tokens=summary_usage.get("prompt_tokens", 0),
                        completion_tokens=summary_usage.get("completion_tokens", 0),
                        total_tokens=summary_usage.get("total_tokens", 0),
                        model=summary_usage.get("model"),
                        role_name="焕",
                    )
                except Exception as e:
                    logger.warning(f"Token 记录失败 (generate_summary): {e}")
            if response and len(response.strip()) > 10:
                profile.summary_text = response.strip()[:200]
                self.db.commit()
        except Exception as e:
            logger.warning(f"画像摘要生成失败: {e}")

    def _infer_attachment_style(self, baseline: dict) -> str | None:
        """基于情绪分布推断依恋风格"""
        total = sum(baseline.values())
        if total < 10:
            return None
        anxious_ratio = (baseline.get("anxious", 0) + baseline.get("lonely", 0) + baseline.get("stressed", 0)) / total
        avoidant_ratio = (baseline.get("angry", 0) + baseline.get("neutral", 0)) / total
        if anxious_ratio > 0.35:
            return "anxious"
        if avoidant_ratio > 0.4:
            return "avoidant"
        return "secure"

    @staticmethod
    def _load_json_list(text: str | None) -> list:
        if not text:
            return []
        try:
            result = json.loads(text)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _load_json_dict(text: str | None) -> dict:
        if not text:
            return {}
        try:
            result = json.loads(text)
            return result if isinstance(result, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _contains_personal_info(text: str) -> bool:
        """Check if text contains personal information keywords."""
        return any(kw in text for kw in ProfileService.PERSONAL_INFO_KEYWORDS)

    async def update_from_conversation(self, user_id: int, user_message: str, user_setting=None):
        """Extract personal info from user message using LLM and update profile."""
        if not self._contains_personal_info(user_message):
            return  # 不包含个人信息，跳过

        try:
            from app.ai.factory import get_emotion_llm_client
            llm = get_emotion_llm_client(user_setting)
        except Exception as e:
            logger.debug(f"画像提取LLM未配置，跳过: {e}")
            return

        prompt = '''从用户消息中提取个人信息，严格以JSON格式返回（无额外文字）：
{
    "nickname": "用户的名字或昵称（如有）",
    "gender": "性别（如有）",
    "interests": ["兴趣爱好列表"],
    "personality_hints": ["性格特征关键词"],
    "other_info": "其他重要个人信息"
}
如果某项没有提到，对应值留空字符串或空列表。'''

        try:
            response, extract_usage = await llm.chat([
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ], temperature=0.1)
            if extract_usage:
                try:
                    TokenService(self.db).record_usage(
                        user_id=user_id,
                        prompt_tokens=extract_usage.get("prompt_tokens", 0),
                        completion_tokens=extract_usage.get("completion_tokens", 0),
                        total_tokens=extract_usage.get("total_tokens", 0),
                        model=extract_usage.get("model"),
                        role_name="焕",
                    )
                except Exception as e:
                    logger.warning(f"Token 记录失败 (update_from_conversation): {e}")
        except Exception as e:
            logger.warning(f"画像提取LLM调用失败: {e}")
            return

        data = self._parse_json(response)
        if not data:
            return

        try:
            profile = self.get_or_create_profile(user_id)

            # 增量更新各字段
            nickname = data.get("nickname", "").strip()
            if nickname:
                existing_summary = profile.summary_text or ""
                if nickname not in existing_summary:
                    profile.summary_text = f"昵称：{nickname}。{existing_summary}".strip()

            gender = data.get("gender", "").strip()
            if gender and gender not in (profile.summary_text or ""):
                profile.summary_text = f"{profile.summary_text or ''} 性别：{gender}。".strip()

            interests = data.get("interests", [])
            if interests:
                existing = self._load_json_list(profile.interests)
                for i in interests:
                    if i and i not in existing:
                        existing.append(i)
                profile.interests = json.dumps(existing[-20:], ensure_ascii=False)

            traits = data.get("personality_hints", [])
            if traits:
                existing = self._load_json_list(profile.personality_traits)
                for t in traits:
                    if t and t not in existing:
                        existing.append(t)
                profile.personality_traits = json.dumps(existing[-10:], ensure_ascii=False)

            other = data.get("other_info", "").strip()
            if other and other not in (profile.summary_text or ""):
                profile.summary_text = f"{profile.summary_text or ''} {other}".strip()

            profile.version += 1
            self.db.commit()
            logger.info(f"用户画像已更新: user_id={user_id}, data={data}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"画像更新失败: {e}")

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """Parse JSON from LLM response, handling markdown fences."""
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
