from datetime import datetime

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    personality_traits: str | None = None
    attachment_style: str | None = None
    core_needs: str | None = None
    emotional_baseline: str | None = None
    trigger_topics: str | None = None
    safe_topics: str | None = None
    interests: str | None = None
    summary_text: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
