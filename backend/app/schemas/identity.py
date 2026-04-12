from datetime import datetime

from pydantic import BaseModel


class AIIdentityResponse(BaseModel):
    id: int
    user_id: int
    ai_name: str
    persona_text: str | None = None
    gender: str | None = None
    appearance: str | None = None
    personality: str | None = None
    speaking_style: str | None = None
    values: str | None = None
    emotional_state: str | None = None
    is_base_locked: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIIdentityUpdate(BaseModel):
    persona_text: str | None = None
    gender: str | None = None
    appearance: str | None = None
    personality: str | None = None
    speaking_style: str | None = None
    values: str | None = None
