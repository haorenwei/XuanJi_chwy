from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tool_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tools.id", ondelete="SET NULL"), nullable=True, index=True
    )
    level: Mapped[str] = mapped_column(String(20), default="info", server_default="info")
    message: Mapped[str] = mapped_column(String(500))
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="操作用户"
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="日志来源模块")
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="操作状态码")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
