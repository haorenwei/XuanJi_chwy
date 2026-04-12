from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.log import LogResponse
from app.services.log_service import LogService

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/")
async def list_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    level: str | None = Query(None, description="日志级别筛选: info/warn/error/debug"),
    source: str | None = Query(None, description="来源模块筛选"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页查询系统日志"""
    svc = LogService(db)
    logs, total = svc.list_logs(
        user_id=current_user.id, limit=limit, offset=offset,
        level=level, source=source,
    )
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [LogResponse.model_validate(log).model_dump() for log in logs],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/stats")
async def log_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """日志统计概览"""
    svc = LogService(db)
    stats = svc.get_stats(user_id=current_user.id)
    return {
        "code": 200,
        "message": "success",
        "data": {"stats": stats},
    }
