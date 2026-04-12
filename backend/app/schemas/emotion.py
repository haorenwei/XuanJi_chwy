from datetime import datetime

from pydantic import BaseModel


class EmotionRecordResponse(BaseModel):
    id: int
    user_id: int
    message_id: int | None = None
    conversation_id: int | None = None
    primary_emotion: str | None = None
    emotion_intensity: str | None = None
    deep_need: str | None = None
    risk_level: str | None = None
    interaction_recommendation: str | None = None
    full_analysis: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
