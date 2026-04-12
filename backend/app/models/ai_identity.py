from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIIdentity(Base):
    __tablename__ = "ai_identities"
    __table_args__ = (
        UniqueConstraint("user_id", "ai_name", name="uq_user_ai_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ai_name: Mapped[str] = mapped_column(String(20))  # 'xuan' | 'ji' | 'qing' | 'huan' | 'yao'

    # Core persona
    persona_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    appearance: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    speaking_style: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object
    values: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object: 世界观/人生观/价值观

    # State & evolution
    emotional_state: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    evolution_log: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    is_base_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
