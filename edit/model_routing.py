"""Классификация сбоев LLM и одноразовый fallback без скрытых циклов."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edit.kie_client import load_llm_config
from edit.llm import ChatModel, get_chat_model


class PolicyBlockedError(RuntimeError):
    """Провайдер отказал по policy; это не сценарий и не обычный transient."""


def is_policy_text(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in (
            "prohibited use policy",
            "sensitive words",
            "safety policy",
            "content policy",
        )
    )


def is_policy_error(exc: Exception) -> bool:
    return is_policy_text(str(exc))


@dataclass
class FailoverChatModel:
    """Меняет модель только при policy-блоке, не повторяет один и тот же вызов."""

    model_ids: list[str]
    temperature: float = 0.0
    disabled_models: set[str] = field(default_factory=set)
    events: list[dict[str, str]] = field(default_factory=list)
    _index: int = 0

    def invoke(self, messages: list[dict[str, str]]) -> Any:
        while self._index < len(self.model_ids):
            model_id = self.model_ids[self._index]
            if model_id in self.disabled_models:
                self._index += 1
                continue
            try:
                response = get_chat_model(model=model_id, temperature=self.temperature).invoke(
                    messages
                )
                text = str(getattr(response, "content", response))
                if is_policy_text(text):
                    raise PolicyBlockedError(text)
                return response
            except Exception as exc:
                if not is_policy_error(exc):
                    raise
                self.disabled_models.add(model_id)
                self.events.append(
                    {
                        "model": model_id,
                        "kind": "policy_block",
                        "error": str(exc),
                    }
                )
                self._index += 1
        raise RuntimeError(
            "Все fallback-модели заблокировали запрос политикой: "
            + ", ".join(self.model_ids)
        )


def get_personal_story_model(
    *, model: str | None = None, temperature: float = 0.0
) -> ChatModel:
    """Модель личного контура с fallback-цепочкой из config."""
    cfg = load_llm_config()
    ids = [model or str(cfg.get("default_model") or "gpt-5-2")]
    ids.extend(str(x) for x in cfg.get("personal_story_fallback_models", []))
    return FailoverChatModel(
        model_ids=list(dict.fromkeys(ids)),
        temperature=temperature,
    )
