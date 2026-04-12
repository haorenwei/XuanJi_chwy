from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskCreate(BaseModel):
    title: str
    description: str | None = None


class TaskUpdate(BaseModel):
    status: TaskStatus | None = None
    result: str | None = None


class TaskStatusUpdate(BaseModel):
    """任务状态更新响应"""
    id: int
    status: str
    result: str | None

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    status: str
    result: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
