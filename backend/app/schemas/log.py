from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LogCreate(BaseModel):
    task_id: int | None = None
    tool_id: int | None = None
    level: str = "info"
    message: str
    details: dict[str, Any] | None = None
    user_id: int | None = None
    source: str | None = None
    status_code: int | None = None


class LogResponse(BaseModel):
    id: int
    task_id: int | None
    tool_id: int | None
    level: str
    message: str
    details: dict[str, Any] | None
    user_id: int | None = None
    source: str | None = None
    status_code: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    items: list[LogResponse]
    total: int
    limit: int
    offset: int


class LogStatsResponse(BaseModel):
    stats: dict[str, int]  # {"info": 10, "warn": 3, "error": 1}
