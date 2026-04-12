from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.log import Log
from app.schemas.log import LogCreate


class LogService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        message: str,
        level: str = "info",
        task_id: int | None = None,
        tool_id: int | None = None,
        details: dict[str, Any] | None = None,
        user_id: int | None = None,
        source: str | None = None,
        status_code: int | None = None,
    ) -> Log:
        entry = Log(
            task_id=task_id,
            tool_id=tool_id,
            level=level,
            message=message,
            details=details,
            user_id=user_id,
            source=source,
            status_code=status_code,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_logs(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        level: str | None = None,
        source: str | None = None,
    ) -> tuple[list[Log], int]:
        """分页查询日志，返回 (日志列表, 总条数)"""
        query = self.db.query(Log).filter(Log.user_id == user_id)
        if level:
            query = query.filter(Log.level == level)
        if source:
            query = query.filter(Log.source == source)
        total = query.count()
        logs = query.order_by(Log.created_at.desc()).offset(offset).limit(limit).all()
        return logs, total

    def get_stats(self, user_id: int) -> dict:
        """日志统计（按 level 分组计数）"""
        results = (
            self.db.query(Log.level, func.count(Log.id))
            .filter(Log.user_id == user_id)
            .group_by(Log.level)
            .all()
        )
        return {level: count for level, count in results}
