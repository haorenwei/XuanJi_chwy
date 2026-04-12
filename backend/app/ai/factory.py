import logging

from app.ai.base import BaseLLMClient
from app.ai.ollama import OllamaClient
from app.ai.online import OnlineLLMClient
from app.core.exceptions import LLMConfigError

logger = logging.getLogger(__name__)

# Ollama 默认地址，仅在用户选择 ollama provider 但未填写 base_url 时使用
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


def _create_online_client(
    user_setting,
    prefix: str,
    role_name: str,
) -> OnlineLLMClient:
    """从 user_setting 中提取 online 模式所需字段，创建 OnlineLLMClient。"""
    api_key = getattr(user_setting, f"{prefix}_api_key", None) or ""
    base_url = getattr(user_setting, f"{prefix}_api_base_url", None) or ""
    model_name = getattr(user_setting, f"{prefix}_model_name", None) or ""

    if not api_key or not base_url:
        missing: list[str] = []
        if not api_key:
            missing.append("api_key")
        if not base_url:
            missing.append("base_url")
        raise LLMConfigError(role_name, missing)

    return OnlineLLMClient(
        api_key=api_key,
        base_url=base_url,
        default_model=model_name or None,
    )


def _create_ollama_client(
    base_url: str | None,
    model_name: str | None,
    role_name: str,
) -> OllamaClient:
    """创建 OllamaClient，校验 model_name 必须存在。"""
    if not model_name:
        raise LLMConfigError(role_name, ["model_name"])

    return OllamaClient(
        base_url=base_url or _DEFAULT_OLLAMA_BASE_URL,
        default_model=model_name,
    )


def get_chat_llm_client(user_setting=None) -> BaseLLMClient:
    """对话AI（玄）客户端。完全从 user_setting 读取，无 Fallback。"""
    role_name = "对话AI（玄）"

    if not user_setting:
        raise LLMConfigError(role_name)

    provider = getattr(user_setting, "llm_provider", None) or ""
    if not provider:
        raise LLMConfigError(role_name, ["provider"])

    if provider == "online":
        return _create_online_client(user_setting, "llm", role_name)
    elif provider == "ollama":
        base_url = getattr(user_setting, "ollama_base_url", None) or ""
        model_name = getattr(user_setting, "ollama_model", None) or ""
        return _create_ollama_client(base_url or None, model_name or None, role_name)
    else:
        raise LLMConfigError(role_name, [f"provider（不支持的值: {provider}）"])


def get_tool_llm_client(user_setting=None) -> BaseLLMClient:
    """工具AI（机）客户端。完全从 user_setting 读取，无 Fallback。"""
    role_name = "工具AI（机）"

    if not user_setting:
        raise LLMConfigError(role_name)

    provider = getattr(user_setting, "tool_llm_provider", None) or ""
    if not provider:
        raise LLMConfigError(role_name, ["provider"])

    if provider == "online":
        return _create_online_client(user_setting, "tool_llm", role_name)
    elif provider == "ollama":
        base_url = getattr(user_setting, "tool_ollama_base_url", None) or ""
        model_name = getattr(user_setting, "tool_ollama_model", None) or ""
        return _create_ollama_client(base_url or None, model_name or None, role_name)
    else:
        raise LLMConfigError(role_name, [f"provider（不支持的值: {provider}）"])


def get_intent_llm_client(user_setting=None) -> BaseLLMClient:
    """意图识别AI（晴）客户端。完全从 user_setting 读取，无 Fallback。"""
    role_name = "意图AI（晴）"

    if not user_setting:
        raise LLMConfigError(role_name)

    provider = getattr(user_setting, "intent_llm_provider", None) or ""
    if not provider:
        raise LLMConfigError(role_name, ["provider"])

    if provider == "online":
        return _create_online_client(user_setting, "intent_llm", role_name)
    elif provider == "ollama":
        model_name = getattr(user_setting, "intent_llm_model_name", None) or ""
        return _create_ollama_client(None, model_name or None, role_name)
    else:
        raise LLMConfigError(role_name, [f"provider（不支持的值: {provider}）"])


def get_emotion_llm_client(user_setting=None) -> BaseLLMClient:
    """情绪管理AI（焕）客户端。完全从 user_setting 读取，无 Fallback。"""
    role_name = "情绪AI（焕）"

    if not user_setting:
        raise LLMConfigError(role_name)

    provider = getattr(user_setting, "emotion_llm_provider", None) or ""
    if not provider:
        raise LLMConfigError(role_name, ["provider"])

    if provider == "online":
        return _create_online_client(user_setting, "emotion_llm", role_name)
    elif provider == "ollama":
        model_name = getattr(user_setting, "emotion_llm_model_name", None) or ""
        return _create_ollama_client(None, model_name or None, role_name)
    else:
        raise LLMConfigError(role_name, [f"provider（不支持的值: {provider}）"])


def get_format_llm_client(user_setting=None) -> BaseLLMClient:
    """格式管理AI（遥）客户端。完全从 user_setting 读取，无 Fallback。"""
    role_name = "格式AI（遥）"

    if not user_setting:
        raise LLMConfigError(role_name)

    provider = getattr(user_setting, "format_llm_provider", None) or ""
    if not provider:
        raise LLMConfigError(role_name, ["provider"])

    if provider == "online":
        return _create_online_client(user_setting, "format_llm", role_name)
    elif provider == "ollama":
        model_name = getattr(user_setting, "format_llm_model_name", None) or ""
        return _create_ollama_client(None, model_name or None, role_name)
    else:
        raise LLMConfigError(role_name, [f"provider（不支持的值: {provider}）"])
