"""Общий LLM-клиент и разбор структурированного JSON."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol


class ChatModel(Protocol):
    def invoke(self, messages: list[dict[str, str]]) -> Any: ...


def get_chat_model(temperature: float = 0.0, model: str = "gpt-4o-mini") -> ChatModel:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, temperature=temperature)


def content_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def parse_json_payload(text: str) -> Any:
    """Строгий разбор JSON: снимает markdown-ограждения, без «починки» схемы."""
    cleaned = text.strip()
    cleaned = _FENCE_RE.sub("", cleaned).strip()
    return json.loads(cleaned)
