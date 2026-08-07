"""Общий LLM-клиент и разбор структурированного JSON.

По умолчанию — KIE (config/llm.yaml). Узлы передают model=/temperature=
через этот адаптер, не ходят в провайдера напрямую.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from edit.kie_client import build_kie_chat_model, load_llm_config, resolve_model_spec


class ChatModel(Protocol):
    def invoke(self, messages: list[dict[str, str]]) -> Any: ...


def get_chat_model(
    temperature: float | None = None,
    model: str | None = None,
) -> ChatModel:
    """Фабрика чат-модели. provider из config/llm.yaml (kie | openai)."""
    cfg = load_llm_config()
    spec = resolve_model_spec(model) if model else None
    provider = (spec.provider if spec and spec.provider else str(cfg.get("provider") or "kie")).lower()
    if provider == "kie":
        return build_kie_chat_model(model=model, temperature=temperature)

    if provider == "aihubmix":
        from langchain_openai import ChatOpenAI

        key = os.environ.get("AIHUBMIX_API_KEY", "").strip()
        if not key:
            raise RuntimeError("AIHUBMIX_API_KEY не задан")
        temp = spec.temperature if spec and temperature is None else (temperature or 0.0)
        return ChatOpenAI(
            model=spec.model_id if spec else (model or "glm-5.2"),
            temperature=temp,
            api_key=key,
            base_url="https://aihubmix.com/v1",
        )

    # fallback: прямой OpenAI (локальная отладка без KIE)
    from langchain_openai import ChatOpenAI

    mid = model or cfg.get("default_model") or "gpt-4o-mini"
    temp = 0.0 if temperature is None else temperature
    if spec is not None and temperature is None:
        temp = spec.temperature
    return ChatOpenAI(model=mid, temperature=temp)


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


def invoke_json(
    llm: ChatModel,
    messages: list[dict[str, str]],
    *,
    retries: int = 2,
) -> Any:
    """Вызов LLM → JSON. При невалидном JSON — ретрай (не чиним руками)."""
    last_err: Exception | None = None
    msgs = list(messages)
    for attempt in range(retries + 1):
        response = llm.invoke(msgs)
        raw_text = content_text(response)
        try:
            return parse_json_payload(raw_text)
        except json.JSONDecodeError as exc:
            last_err = exc
            msgs = list(messages) + [
                {"role": "assistant", "content": raw_text},
                {
                    "role": "user",
                    "content": (
                        "Ответ не является валидным JSON. "
                        "Верни ТОЛЬКО валидный JSON без markdown и пояснений."
                    ),
                },
            ]
    raise ValueError(f"LLM не вернул валидный JSON за {retries + 1} попыток: {last_err}")
