import json
import re
from typing import AsyncIterator, Callable

import httpx

from app.ai.base import BaseLLMClient


class OnlineLLMClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
    ):
        if not api_key:
            raise ValueError("OnlineLLMClient requires a valid api_key")
        self.api_key = api_key
        if not base_url:
            raise ValueError("OnlineLLMClient requires a valid base_url")
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model  # model 可以为 None，由调用方决定

    def _headers(self) -> dict[str, str]:
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
    ) -> tuple[str, dict | None]:
        used_model = model or self.default_model
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": used_model,
                    "messages": messages,
                    "temperature": temperature,
                    **({"max_tokens": max_tokens} if max_tokens else {}),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
            usage = data.get("usage")
            if usage and "model" not in usage:
                usage["model"] = used_model
            return content, usage

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        usage_callback: Callable[[dict], None] | None = None,
    ) -> AsyncIterator[str]:
        used_model = model or self.default_model
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": used_model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                    **({"max_tokens": max_tokens} if max_tokens else {}),
                },
            ) as resp:
                buffer = ""
                in_think = False
                usage_data = None
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        # Capture usage from the last chunk if present
                        if "usage" in data and data["usage"]:
                            usage_data = data["usage"]
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        if delta := choices[0].get("delta", {}).get("content"):
                            buffer += delta
                            while True:
                                if in_think:
                                    end_idx = buffer.find("</think>")
                                    if end_idx != -1:
                                        buffer = buffer[end_idx + 8:]
                                        in_think = False
                                        continue
                                    else:
                                        if len(buffer) > 7:
                                            buffer = buffer[-7:]
                                        break
                                else:
                                    start_idx = buffer.find("<think>")
                                    if start_idx != -1:
                                        if start_idx > 0:
                                            yield buffer[:start_idx]
                                        buffer = buffer[start_idx + 7:]
                                        in_think = True
                                        continue
                                    else:
                                        safe_end = len(buffer)
                                        for i in range(1, min(7, len(buffer) + 1)):
                                            if "<think>".startswith(buffer[-i:]):
                                                safe_end = len(buffer) - i
                                                break
                                        if safe_end > 0:
                                            yield buffer[:safe_end]
                                        buffer = buffer[safe_end:]
                                        break
                if buffer and not in_think:
                    yield buffer
                if usage_callback and usage_data:
                    if "model" not in usage_data:
                        usage_data["model"] = used_model
                    usage_callback(usage_data)
