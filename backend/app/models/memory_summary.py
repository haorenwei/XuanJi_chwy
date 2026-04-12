from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MemorySummary(Base):
    __tablename__ = "memory_summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    period_type: Mapped[str] = mapped_column(String(20))  # 'daily' | 'weekly' | 'monthly' | 'yearly'
    period_start: Mapped[datetime] = mapped_column(DateTime)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_emotions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    key_topics: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    important_events: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    source_message_count: Mapped[int] = mapped_column(Integer, default=0)
    source_summary_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
