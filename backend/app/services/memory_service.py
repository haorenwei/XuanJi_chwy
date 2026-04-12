import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.ai.factory import get_emotion_llm_client
from app.core.exceptions import LLMConfigError
from app.models.conversation import Message
from app.models.emotion import EmotionRecord
from app.models.memory_summary import MemorySummary
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)


COMPRESS_PROMPT = """\
请将以下{period_label}的对话记录压缩为一段精炼的记忆摘要。

要求：
1. 保留情绪显著的事件（详细描述）
2. 保留重要话题和关键信息
3. 将日常/平淡的对话压缩为简短概括
4. 提取关键情绪和关键话题标签
5. 标记需要长期记住的重要事件

原始内容：
{content}

请严格以JSON格式返回：
{{
  "summary": "压缩后的记忆摘要文本",
  "key_emotions": ["情绪标签1", "情绪标签2"],
  "key_topics": ["话题标签1", "话题标签2"],
  "important_events": ["需要长期记忆的重要事件描述1", "重要事件2"]
}}
"""


class MemoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_relevant_memories(self, user_id: int, query_text: str, limit: int = 5) -> list[MemorySummary]:
        """Find most relevant memory summaries using keyword overlap + recency scoring."""
        # Get all summaries for user, ordered by recency
        summaries = (
            self.db.query(MemorySummary)
            .filter(MemorySummary.user_id == user_id)
            .order_by(desc(MemorySummary.period_start))
            .limit(100)
            .all()
        )

        if not summaries:
            return []

        query_tokens = set(query_text.lower().split())

        scored = []
        now = datetime.now()
        for s in summaries:
            score = 0.0

            # Keyword overlap with topics
            if s.key_topics:
                try:
                    topics = json.loads(s.key_topics)
                    if isinstance(topics, list):
                        topic_text = " ".join(topics).lower()
                        overlap = len(query_tokens & set(topic_text.split()))
                        score += overlap * 3.0
                except (json.JSONDecodeError, TypeError):
                    pass

            # Keyword overlap with summary text
            if s.summary_text:
                summary_tokens = set(s.summary_text.lower().split())
                overlap = len(query_tokens & summary_tokens)
                score += overlap * 1.0

            # Recency bias (decay over days)
            days_old = (now - s.period_start).days
            recency_score = max(0, 10 - days_old * 0.1)
            score += recency_score

            # Emotional significance bonus
            if s.important_events:
                try:
                    events = json.loads(s.important_events)
                    if isinstance(events, list) and events:
                        score += len(events) * 2.0
                except (json.JSONDecodeError, TypeError):
                    pass

            # Granularity preference: daily > weekly > monthly > yearly
            granularity_bonus = {"daily": 2, "weekly": 1.5, "monthly": 1, "yearly": 0.5}
            score += granularity_bonus.get(s.period_type, 0)

            scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    async def compress_day(self, user_id: int, date: datetime, user_setting=None) -> MemorySummary | None:
        """Compress a day's messages into a daily summary."""
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        messages = (
            self.db.query(Message)
            .filter(
                Message.user_id == user_id,
                Message.is_summarized == False,
                Message.created_at >= day_start,
                Message.created_at < day_end,
            )
            .order_by(Message.created_at)
            .all()
        )

        if not messages:
            return None

        # Build content text from messages
        content_parts = []
        for msg in messages:
            content_parts.append(f"[{msg.role}] {msg.content[:500]}")
        content = "\n".join(content_parts)

        # Check for high-emotion messages
        high_emotion_msgs = []
        for msg in messages:
            if msg.emotion_snapshot:
                try:
                    snap = json.loads(msg.emotion_snapshot)
                    if snap.get("emotion_intensity") == "high" or snap.get("risk_level") in ("moderate", "high"):
                        high_emotion_msgs.append(msg.content[:200])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Call LLM to compress
        summary_data = await self._llm_compress("一天", content, user_setting, user_id=user_id)
        if not summary_data:
            return None

        # Merge high-emotion events
        important = summary_data.get("important_events", [])
        if high_emotion_msgs:
            for hem in high_emotion_msgs:
                if hem not in important:
                    important.append(hem)

        summary = MemorySummary(
            user_id=user_id,
            period_type="daily",
            period_start=day_start,
            period_end=day_end,
            summary_text=summary_data.get("summary", ""),
            key_emotions=json.dumps(summary_data.get("key_emotions", []), ensure_ascii=False),
            key_topics=json.dumps(summary_data.get("key_topics", []), ensure_ascii=False),
            important_events=json.dumps(important, ensure_ascii=False),
            source_message_count=len(messages),
        )
        self.db.add(summary)

        # Mark messages as summarized
        msg_ids = [m.id for m in messages]
        self.db.query(Message).filter(Message.id.in_(msg_ids)).update(
            {"is_summarized": True}, synchronize_session=False
        )
        self.db.commit()
        self.db.refresh(summary)
        return summary

    async def compress_week(self, user_id: int, week_start: datetime, user_setting=None) -> MemorySummary | None:
        """Merge daily summaries into a weekly summary."""
        week_end = week_start + timedelta(days=7)
        return await self._compress_period(user_id, "weekly", "一周", week_start, week_end, "daily", user_setting)

    async def compress_month(self, user_id: int, year: int, month: int, user_setting=None) -> MemorySummary | None:
        """Merge weekly summaries into a monthly summary."""
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)
        return await self._compress_period(user_id, "monthly", "一个月", month_start, month_end, "weekly", user_setting)

    async def compress_year(self, user_id: int, year: int, user_setting=None) -> MemorySummary | None:
        """Merge monthly summaries into a yearly summary."""
        year_start = datetime(year, 1, 1)
        year_end = datetime(year + 1, 1, 1)
        return await self._compress_period(user_id, "yearly", "一年", year_start, year_end, "monthly", user_setting)

    async def _compress_period(
        self, user_id, period_type, period_label, start, end, source_type, user_setting
    ) -> MemorySummary | None:
        """Generic period compression: merge source_type summaries into a higher-level summary."""
        sources = (
            self.db.query(MemorySummary)
            .filter(
                MemorySummary.user_id == user_id,
                MemorySummary.period_type == source_type,
                MemorySummary.period_start >= start,
                MemorySummary.period_start < end,
            )
            .order_by(MemorySummary.period_start)
            .all()
        )

        if not sources:
            return None

        content_parts = []
        all_important = []
        total_msgs = 0
        source_ids = []

        for s in sources:
            content_parts.append(s.summary_text or "")
            total_msgs += s.source_message_count
            source_ids.append(s.id)
            if s.important_events:
                try:
                    events = json.loads(s.important_events)
                    if isinstance(events, list):
                        all_important.extend(events)
                except (json.JSONDecodeError, TypeError):
                    pass

        content = "\n---\n".join(content_parts)
        summary_data = await self._llm_compress(period_label, content, user_setting, user_id=user_id)
        if not summary_data:
            return None

        # Carry forward important events from sources
        new_important = summary_data.get("important_events", [])
        for evt in all_important:
            if evt not in new_important:
                new_important.append(evt)

        summary = MemorySummary(
            user_id=user_id,
            period_type=period_type,
            period_start=start,
            period_end=end,
            summary_text=summary_data.get("summary", ""),
            key_emotions=json.dumps(summary_data.get("key_emotions", []), ensure_ascii=False),
            key_topics=json.dumps(summary_data.get("key_topics", []), ensure_ascii=False),
            important_events=json.dumps(new_important, ensure_ascii=False),
            source_message_count=total_msgs,
            source_summary_ids=json.dumps(source_ids),
        )
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary

    async def _llm_compress(self, period_label: str, content: str, user_setting=None, user_id: int = None) -> dict | None:
        """Call LLM to compress content into structured summary."""
        try:
            prompt = COMPRESS_PROMPT.format(period_label=period_label, content=content[:8000])
            llm = get_emotion_llm_client(user_setting)
            response, compress_usage = await llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            if compress_usage and user_id is not None:
                try:
                    TokenService(self.db).record_usage(
                        user_id=user_id,
                        prompt_tokens=compress_usage.get("prompt_tokens", 0),
                        completion_tokens=compress_usage.get("completion_tokens", 0),
                        total_tokens=compress_usage.get("total_tokens", 0),
                        model=compress_usage.get("model"),
                        role_name="焕",
                    )
                except Exception as e:
                    logger.warning(f"Token 记录失败 (_llm_compress): {e}")
            return self._parse_json(response)
        except LLMConfigError as e:
            logger.warning("记忆压缩所需的情绪AI（焕）配置缺失，跳过压缩: %s", e)
            return None
        except Exception:
            return None

    @staticmethod
    def should_preserve(emotion_data: dict) -> bool:
        """Determine if an event has high emotional significance and should resist decay."""
        intensity = emotion_data.get("emotion_intensity", "")
        risk = emotion_data.get("risk_level", "")
        return intensity == "high" or risk in ("moderate", "high")

    def get_memory_context(self, user_id: int, query_text: str, max_tokens: int = 1000) -> str:
        """Get relevant memories as a formatted context string.
        Falls back to short-term memory (recent messages) when no summaries exist."""
        memories = self.get_relevant_memories(user_id, query_text, limit=5)
        if not memories:
            # Fallback: 短期记忆
            return self._get_short_term_memory(user_id, max_tokens)

        parts = ["[相关记忆]"]
        char_count = 0
        for m in memories:
            text = m.summary_text or ""
            # Rough token estimate: 1 Chinese char ~ 1.5 tokens
            if char_count + len(text) > max_tokens:
                text = text[:max_tokens - char_count]
            parts.append(f"({m.period_type} {m.period_start.strftime('%Y-%m-%d')}): {text}")
            char_count += len(text)
            if char_count >= max_tokens:
                break

        return "\n".join(parts)

    def _get_short_term_memory(self, user_id: int, max_tokens: int = 1000) -> str:
        """Fallback: build context from recent messages when no memory summaries exist."""
        recent_messages = (
            self.db.query(Message)
            .filter(Message.user_id == user_id)
            .order_by(desc(Message.created_at))
            .limit(20)
            .all()
        )
        if not recent_messages:
            return ""

        # Reverse to chronological order
        recent_messages = list(reversed(recent_messages))

        parts = ["[短期记忆]"]
        char_count = 0
        for msg in recent_messages:
            line = f"[{msg.role}] {msg.content[:200]}"
            if char_count + len(line) > max_tokens:
                break
            parts.append(line)
            char_count += len(line)

        return "\n".join(parts) if len(parts) > 1 else ""

    async def compress_recent(self, user_id: int, user_setting=None) -> MemorySummary | None:
        """Compress today's unsummarized messages. Meant to be called as a background task
        after a conversation ends. Skips if fewer than 5 messages today."""
        today = datetime.now()
        day_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Check message count first
        msg_count = (
            self.db.query(func.count(Message.id))
            .filter(
                Message.user_id == user_id,
                Message.is_summarized == False,
                Message.created_at >= day_start,
                Message.created_at < day_end,
            )
            .scalar()
        )
        if msg_count < 5:
            logger.debug(f"今日未摘要消息仅{msg_count}条，跳过压缩")
            return None

        return await self.compress_day(user_id, today, user_setting)

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
