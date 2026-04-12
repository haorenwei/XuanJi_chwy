import json
from typing import AsyncIterator, Callable

import httpx

from app.ai.base import BaseLLMClient
from app.core.config import settings


class OllamaClient(BaseLLMClient):
    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.default_model = default_model or settings.ollama_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> tuple[str, dict | None]:
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
            body = resp.json()
            used_model = model or self.default_model
            usage = {
                "prompt_tokens": body.get("prompt_eval_count", 0),
                "completion_tokens": body.get("eval_count", 0),
                "total_tokens": body.get("prompt_eval_count", 0) + body.get("eval_count", 0),
                "model": used_model,
            }
            return body["message"]["content"], usage

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        usage_callback: Callable[[dict], None] | None = None,
    ) -> AsyncIterator[str]:
        used_model = model or self.default_model
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": used_model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        **({"num_predict": max_tokens} if max_tokens else {}),
                    },
                },
            ) as resp:
                prompt_tokens = 0
                eval_tokens = 0
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if content := data.get("message", {}).get("content"):
                            yield content
                        # Ollama sends counts in the final chunk (done=true)
                        if data.get("done"):
                            prompt_tokens = data.get("prompt_eval_count", 0)
                            eval_tokens = data.get("eval_count", 0)
                if usage_callback and (prompt_tokens or eval_tokens):
                    usage_callback({
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": eval_tokens,
                        "total_tokens": prompt_tokens + eval_tokens,
                        "model": used_model,
                    })
