import json
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator, Callable


class BaseLLMClient(ABC):
    """Unified interface for all LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> tuple[str, dict | None]:
        """Send messages and get a complete response.
        Returns (content, usage) where usage may be None."""
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        usage_callback: Callable[[dict], None] | None = None,
    ) -> AsyncIterator[str]:
        """Send messages and stream the response token by token.
        If usage_callback is provided and usage data is available,
        it will be called with the usage dict after streaming completes."""
        ...


SKILLS_DIR = Path(__file__).parent / "skills"


@lru_cache(maxsize=None)
def load_prompt(role: str, filename: str) -> str:
    """从 skill 目录加载 prompt 模板文件"""
    path = SKILLS_DIR / f"xuanji-{role}" / filename
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=None)
def load_json_config(role: str, filename: str) -> dict:
    """从 skill 目录加载 JSON 配置文件"""
    path = SKILLS_DIR / f"xuanji-{role}" / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_prompt_sections(role: str, filename: str) -> dict[str, str]:
    """加载含分段标记的 prompt 文件，返回 {section_name: content}"""
    raw = load_prompt(role, filename)
    sections = {}
    current_key = None
    lines = []
    for line in raw.split("\n"):
        if line.startswith("---SECTION:") and line.endswith("---"):
            if current_key:
                sections[current_key] = "\n".join(lines).strip()
            current_key = line[len("---SECTION:"):-len("---")].strip()
            lines = []
        else:
            lines.append(line)
    if current_key:
        sections[current_key] = "\n".join(lines).strip()
    return sections
