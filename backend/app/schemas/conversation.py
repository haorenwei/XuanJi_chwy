from datetime import datetime

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str | None = None
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    role: str
    content: str
    metadata_json: str | None = None
    emotion_snapshot: str | None = None
    is_summarized: bool
    created_at: datetime

    model_config = {"from_attributes": True}
