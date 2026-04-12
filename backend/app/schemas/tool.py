from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ToolCreate(BaseModel):
    name: str
    description: str
    description_zh: Optional[str] = None
    code: str
    language: str = "python"


class ToolBrief(BaseModel):
    id: int
    name: str
    description: str
    description_zh: Optional[str] = None
    language: str
    version: int
    is_builtin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    description_zh: Optional[str] = None
    code: str | None = None
    language: str | None = None


class ToolImportItem(BaseModel):
    name: str
    description: str = ""
    description_zh: Optional[str] = None
    code: str
    language: str = "python"
    tool_type: Optional[str] = "atomic"


class ToolExportItem(BaseModel):
    name: str
    description: str
    description_zh: Optional[str] = None
    code: str
    language: str
    version: int
    tool_type: Optional[str] = "atomic"

    model_config = {"from_attributes": True}


class ToolResponse(ToolBrief):
    code: str
    created_by: int | None
    updated_at: datetime


class ToolVersionResponse(BaseModel):
    id: int
    tool_id: int
    version: int
    code: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None
    change_summary: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}
