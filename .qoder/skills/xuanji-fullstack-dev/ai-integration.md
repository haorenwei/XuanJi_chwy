# AI Integration Guide

## Architecture

```
app/ai/
├── __init__.py
├── base.py          # Abstract base client
├── ollama.py        # Ollama local model client
├── online.py        # Online LLM API client (OpenAI-compatible)
└── factory.py       # Client factory based on config
```

## Base Interface

```python
# app/ai/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator

class BaseLLMClient(ABC):
    """Unified interface for all LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Send messages and get a complete response."""
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Send messages and stream the response token by token."""
        ...
```

## Ollama Client

```python
# app/ai/ollama.py
import httpx
from typing import AsyncIterator
from app.ai.base import BaseLLMClient
from app.core.config import settings

class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str | None = None, default_model: str = "qwen2.5"):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.default_model = default_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model or self.default_model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        **({"num_predict": max_tokens} if max_tokens else {}),
                    },
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model or self.default_model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        **({"num_predict": max_tokens} if max_tokens else {}),
                    },
                },
            ) as resp:
                import json
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if content := data.get("message", {}).get("content"):
                            yield content
```

## Online LLM Client (OpenAI-compatible)

```python
# app/ai/online.py
import httpx
from typing import AsyncIterator
from app.ai.base import BaseLLMClient
from app.core.config import settings

class OnlineLLMClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
    ):
        self.api_key = api_key or settings.llm_api_key
        self.base_url = (base_url or settings.llm_api_base_url).rstrip("/")
        self.default_model = default_model or settings.llm_model_name

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": model or self.default_model,
                    "messages": messages,
                    "temperature": temperature,
                    **({"max_tokens": max_tokens} if max_tokens else {}),
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": model or self.default_model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                    **({"max_tokens": max_tokens} if max_tokens else {}),
                },
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        data = json.loads(line[6:])
                        if delta := data["choices"][0].get("delta", {}).get("content"):
                            yield delta
```

## Factory Pattern

```python
# app/ai/factory.py
from app.ai.base import BaseLLMClient
from app.ai.ollama import OllamaClient
from app.ai.online import OnlineLLMClient
from app.core.config import settings

def get_llm_client() -> BaseLLMClient:
    """Create LLM client based on LLM_PROVIDER env var."""
    if settings.llm_provider == "ollama":
        return OllamaClient()
    elif settings.llm_provider == "online":
        return OnlineLLMClient()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

## Usage in FastAPI Endpoints

```python
# app/api/v1/chat.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.ai.factory import get_llm_client
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    stream: bool = False

@router.post("/")
async def chat(req: ChatRequest):
    client = get_llm_client()

    if req.stream:
        async def generate():
            async for chunk in client.stream_chat(req.messages):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")

    result = await client.chat(req.messages)
    return {"code": 200, "message": "success", "data": {"content": result}}
```

## Ollama Model Management

Common commands:
```bash
# List installed models
ollama list

# Pull a model
ollama pull qwen2.5
ollama pull llama3

# Run interactive chat (testing)
ollama run qwen2.5

# Check running models
ollama ps
```

## Environment Variables for AI

```bash
# .env

# Provider selection: ollama | online
LLM_PROVIDER=ollama

# Ollama config
OLLAMA_BASE_URL=http://localhost:11434

# Online LLM config (OpenAI-compatible)
LLM_API_KEY=sk-xxx
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o
```

## Error Handling

Wrap LLM calls with proper error handling:

```python
from httpx import HTTPStatusError, ConnectError

async def safe_chat(client: BaseLLMClient, messages: list[dict]) -> str:
    try:
        return await client.chat(messages)
    except ConnectError:
        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable. Check if Ollama is running."
        )
    except HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM API error: {e.response.status_code}"
        )
```
