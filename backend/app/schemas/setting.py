from datetime import datetime

from pydantic import BaseModel, field_validator


class SettingUpdate(BaseModel):
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_api_base_url: str | None = None
    llm_model_name: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    # Tool Generation AI config
    tool_llm_provider: str | None = None
    tool_llm_api_key: str | None = None
    tool_llm_api_base_url: str | None = None
    tool_llm_model_name: str | None = None
    tool_ollama_base_url: str | None = None
    tool_ollama_model: str | None = None
    # Intent Recognition AI config
    intent_llm_provider: str | None = None
    intent_llm_api_key: str | None = None
    intent_llm_api_base_url: str | None = None
    intent_llm_model_name: str | None = None
    # Emotion AI config (焕)
    emotion_llm_provider: str | None = None
    emotion_llm_api_key: str | None = None
    emotion_llm_api_base_url: str | None = None
    emotion_llm_model_name: str | None = None
    # Format AI config (遥)
    format_llm_provider: str | None = None
    format_llm_api_key: str | None = None
    format_llm_api_base_url: str | None = None
    format_llm_model_name: str | None = None
    show_tool_result: bool | None = None
    show_collaboration: bool | None = None
    token_monthly_budget: int | None = None


class SettingResponse(BaseModel):
    id: int
    user_id: int
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_api_base_url: str | None = None
    llm_model_name: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    # Tool Generation AI config
    tool_llm_provider: str | None = None
    tool_llm_api_key: str | None = None
    tool_llm_api_base_url: str | None = None
    tool_llm_model_name: str | None = None
    tool_ollama_base_url: str | None = None
    tool_ollama_model: str | None = None
    # Intent Recognition AI config
    intent_llm_provider: str | None = None
    intent_llm_api_key: str | None = None
    intent_llm_api_base_url: str | None = None
    intent_llm_model_name: str | None = None
    # Emotion AI config (焕)
    emotion_llm_provider: str | None = None
    emotion_llm_api_key: str | None = None
    emotion_llm_api_base_url: str | None = None
    emotion_llm_model_name: str | None = None
    # Format AI config (遥)
    format_llm_provider: str | None = None
    format_llm_api_key: str | None = None
    format_llm_api_base_url: str | None = None
    format_llm_model_name: str | None = None
    show_tool_result: bool | None = None
    show_collaboration: bool | None = None
    token_monthly_budget: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("llm_api_key", "tool_llm_api_key", "intent_llm_api_key", "emotion_llm_api_key", "format_llm_api_key", mode="before")
    @classmethod
    def mask_api_key(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) <= 8:
            return "****"
        return v[:4] + "***" + v[-4:]
