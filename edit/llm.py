"""Общий LLM-клиент и разбор структурированного JSON.

По умолчанию — KIE (config/llm.yaml). Узлы передают model=/temperature=
через этот адаптер, не ходят в провайдера напрямую.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Protocol

from edit.kie_client import (
    KieAPIError,
    build_kie_chat_model,
    load_llm_config,
    resolve_model_spec,
)


class ChatModel(Protocol):
    def invoke(self, messages: list[dict[str, str]], **kwargs: Any) -> Any: ...


def _is_transient_llm_error(exc: Exception) -> bool:
    """Пустой choices / сеть / 5xx — имеет смысл повторить тот же вызов."""
    if isinstance(exc, KieAPIError):
        return bool(exc.retryable)
    msg = str(exc).lower()
    if "daily limit" in msg or "exceeded" in msg:
        return False
    if isinstance(exc, TypeError) and "nonetype" in msg:
        return True
    return any(
        marker in msg
        for marker in (
            "choices",
            "timeout",
            "timed out",
            "rate limit",
            "429",
            "502",
            "503",
            "504",
            "connection",
            "temporarily unavailable",
        )
    )


class RetryingChatModel:
    """Обёртка над ChatModel: ретраи на transient-сбоях провайдера."""

    def __init__(self, inner: ChatModel, *, retries: int = 6, base_delay: float = 3.0):
        self.inner = inner
        self.retries = retries
        self.base_delay = base_delay

    def invoke(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        last_err: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                return self.inner.invoke(messages, **kwargs)
            except Exception as exc:
                last_err = exc
                if not _is_transient_llm_error(exc) or attempt >= self.retries:
                    raise
                delay = min(60.0, self.base_delay * (2**attempt))
                print(f"LLM retry {attempt + 1}/{self.retries}: {exc}; sleep {delay:.0f}s")
                time.sleep(delay)
        assert last_err is not None
        raise last_err


def get_chat_model(
    temperature: float | None = None,
    model: str | None = None,
) -> ChatModel:
    """Фабрика чат-модели. provider из config/llm.yaml (kie | openai)."""
    cfg = load_llm_config()
    spec = resolve_model_spec(model) if model else None
    provider = (spec.provider if spec and spec.provider else str(cfg.get("provider") or "kie")).lower()
    if provider == "kie":
        return RetryingChatModel(build_kie_chat_model(model=model, temperature=temperature))

    if provider == "aihubmix":
        from langchain_openai import ChatOpenAI

        key = os.environ.get("AIHUBMIX_API_KEY", "").strip()
        if not key:
            raise RuntimeError("AIHUBMIX_API_KEY не задан")
        temp = spec.temperature if spec and temperature is None else (temperature or 0.0)
        return RetryingChatModel(
            ChatOpenAI(
                model=spec.model_id if spec else (model or "glm-5.2"),
                temperature=temp,
                api_key=key,
                base_url="https://aihubmix.com/v1",
            )
        )

    # fallback: прямой OpenAI (локальная отладка без KIE)
    from langchain_openai import ChatOpenAI

    mid = model or cfg.get("default_model") or "gpt-4o-mini"
    temp = 0.0 if temperature is None else temperature
    if spec is not None and temperature is None:
        temp = spec.temperature
    return RetryingChatModel(ChatOpenAI(model=mid, temperature=temp))


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
