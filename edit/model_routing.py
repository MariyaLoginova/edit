"""Классификация сбоев LLM и одноразовый fallback без скрытых циклов."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edit.kie_client import KieAPIError, load_llm_config
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

    def invoke(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        while self._index < len(self.model_ids):
            model_id = self.model_ids[self._index]
            if model_id in self.disabled_models:
                self._index += 1
                continue
            try:
                response = get_chat_model(model=model_id, temperature=self.temperature).invoke(
                    messages, **kwargs
                )
                text = str(getattr(response, "content", response))
                if is_policy_text(text):
                    raise PolicyBlockedError(text)
                return response
            except Exception as exc:
                policy = is_policy_error(exc) or isinstance(exc, PolicyBlockedError)
                server = isinstance(exc, KieAPIError) and (
                    (exc.code in {500, 502, 503, 504})
                    or "server exception" in str(exc).lower()
                )
                # googleSearch иногда уходит в долгий timeout — пробуем следующую модель.
                timed_out = isinstance(exc, TimeoutError) or "timed out" in str(exc).lower()
                if not policy and not server and not timed_out:
                    raise
                kind = (
                    "policy_block"
                    if policy
                    else ("timeout_failover" if timed_out else "server_failover")
                )
                self.disabled_models.add(model_id)
                self.events.append(
                    {
                        "model": model_id,
                        "kind": kind,
                        "error": str(exc),
                    }
                )
                self._index += 1
        raise RuntimeError(
            "Все fallback-модели отказали (policy/server): " + ", ".join(self.model_ids)
        )


def get_personal_story_model(
    *, model: str | None = None, temperature: float = 0.0
) -> ChatModel:
    """Модель личного контура с fallback-цепочкой из config.

    Цепочка: default (gpt-5-2) → gemini-3-6 → gemini-3.5 → … .
    gemini-2.5-flash сюда только как аварийный хвост из yaml, не для A1/B1.
    """
    cfg = load_llm_config()
    ids = [model or str(cfg.get("default_model") or "gpt-5-2")]
    ids.extend(str(x) for x in cfg.get("personal_story_fallback_models", []))
    return FailoverChatModel(
        model_ids=list(dict.fromkeys(ids)),
        temperature=temperature,
    )


def get_topic_pass_model(
    *, model: str | None = None, temperature: float = 0.0
) -> ChatModel:
    """Long-context модель для выбора тем/тегов (A1/A2+B1 whole-book).

    По умолчанию topic_pass_model из config (gemini-2.5-flash). В редактуру
    (E/C/D) эту модель не ставим основной — см. get_personal_story_model.
    """
    cfg = load_llm_config()
    mid = model or str(cfg.get("topic_pass_model") or "gemini-2.5-flash")
    return get_chat_model(model=mid, temperature=temperature)


def get_research_enrich_model(
    *, model: str | None = None, temperature: float = 0.0
) -> ChatModel:
    """C1.5: Gemini с googleSearch на KIE (не gpt — у него нет grounding)."""
    cfg = load_llm_config()
    ids = [model or str(cfg.get("research_enrich_model") or "gemini-3-6-flash")]
    ids.extend(str(x) for x in cfg.get("research_enrich_fallback_models", []))
    # Хвост: 2.5-flash умеет googleSearch (проверено smoke).
    ids.append("gemini-2.5-flash")
    return FailoverChatModel(
        model_ids=list(dict.fromkeys(ids)),
        temperature=temperature,
    )
