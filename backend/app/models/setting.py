from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    llm_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    llm_api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    llm_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ollama_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ollama_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Tool Generation AI config (fallback to chat AI if not set)
    tool_llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tool_llm_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tool_llm_api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tool_llm_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_ollama_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tool_ollama_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Intent Recognition AI config (fallback to chat AI if not set)
    intent_llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    intent_llm_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    intent_llm_api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    intent_llm_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Emotion AI config (焕, fallback to chat AI if not set)
    emotion_llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    emotion_llm_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    emotion_llm_api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    emotion_llm_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Format AI config (遥, fallback to chat AI if not set)
    format_llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    format_llm_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    format_llm_api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    format_llm_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Chat preferences
    show_tool_result: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    show_collaboration: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    token_monthly_budget: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
