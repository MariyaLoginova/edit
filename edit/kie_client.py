"""Тонкий адаптер KIE (OpenAI-compatible chat completions).

Паттерн как в CineFlow: ключ из env, модель/путь из config/llm.yaml,
узлы зовут LLM только через get_chat_model / этот модуль.

KIE иногда отвечает HTTP 200 с телом `{code, msg, data}` вместо
OpenAI-формата — тогда langchain видит choices=null. Здесь ловим это явно.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
LLM_CONFIG_PATH = ROOT / "config" / "llm.yaml"


class KieAPIError(RuntimeError):
    """Ошибка конверта KIE (лимит, биллинг, пустой data)."""

    def __init__(self, message: str, *, code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    path_prefix: str
    temperature: float = 0.0
    provider: str | None = None


@lru_cache(maxsize=1)
def load_llm_config() -> dict[str, Any]:
    load_dotenv(ROOT / ".env", override=False)
    with LLM_CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def clear_llm_config_cache() -> None:
    load_llm_config.cache_clear()


def list_configured_models() -> list[str]:
    cfg = load_llm_config()
    return list((cfg.get("models") or {}).keys())


def resolve_model_spec(model: str | None = None) -> ModelSpec:
    cfg = load_llm_config()
    model_id = model or cfg.get("default_model") or "gpt-5-2"
    models = cfg.get("models") or {}
    if model_id not in models:
        raise KeyError(
            f"Модель {model_id!r} нет в config/llm.yaml → models. "
            f"Доступны: {sorted(models)}"
        )
    raw = models[model_id] or {}
    path_prefix = str(raw.get("path_prefix") or f"{model_id}/v1").strip("/")
    return ModelSpec(
        model_id=model_id,
        path_prefix=path_prefix,
        temperature=float(raw.get("temperature", 0.0)),
        provider=str(raw.get("provider") or "").lower() or None,
    )


def kie_api_key() -> str:
    cfg = load_llm_config()
    env_name = cfg.get("api_key_env") or "KIE_API_KEY"
    key = os.environ.get(env_name, "").strip()
    if not key:
        raise RuntimeError(
            f"{env_name} не задан. Положите ключ в .env (файл в .gitignore) "
            "или в секреты окружения."
        )
    return key


def kie_base_url_for(model: str | None = None) -> str:
    """База для ChatOpenAI: …/{path_prefix} → …/chat/completions."""
    cfg = load_llm_config()
    root = str(cfg.get("base_url") or "https://api.kie.ai").rstrip("/")
    spec = resolve_model_spec(model)
    return f"{root}/{spec.path_prefix}"


def _raise_if_kie_envelope(payload: dict[str, Any]) -> None:
    """KIE error envelope: {code, msg, data} при HTTP 200."""
    if "choices" in payload:
        return
    code = payload.get("code")
    msg = payload.get("msg") or payload.get("message") or ""
    if code is None and not msg:
        return
    text = str(msg)
    low = text.lower()
    code_int = int(code) if isinstance(code, int) else None
    retryable = any(
        marker in low
        for marker in (
            "timeout",
            "temporarily",
            "try again",
            "rate limit",
            "server exception",
            "429",
            "500",
            "502",
            "503",
            "504",
        )
    ) or code_int in {408, 429, 500, 502, 503, 504}
    # дневной лимит / баланс — не ретраить
    if "daily limit" in low or code_int in {402, 433}:
        retryable = False
    raise KieAPIError(
        f"KIE error code={code}: {text or payload}",
        code=code_int,
        retryable=retryable,
    )


@dataclass
class _SimpleMessage:
    content: str


@dataclass
class _SimpleResponse:
    content: str
    raw: dict[str, Any]

    @property
    def response_metadata(self) -> dict[str, Any]:
        usage = self.raw.get("usage") or {}
        return {"token_usage": usage, "model_name": self.raw.get("model")}


class KieChatModel:
    """Прямой OpenAI-совместимый клиент KIE с понятными ошибками квоты."""

    def __init__(self, *, model: str, temperature: float, api_key: str, base_url: str):
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def invoke(self, messages: list[dict[str, str]]) -> _SimpleResponse:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": messages,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                raw_text = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise KieAPIError(
                f"KIE HTTP {exc.code}: {body[:500]}",
                code=exc.code,
                retryable=exc.code in {408, 429, 500, 502, 503, 504},
            ) from exc
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise KieAPIError(f"KIE вернул не-JSON: {raw_text[:300]}", retryable=True) from exc
        if not isinstance(data, dict):
            raise KieAPIError(f"KIE: ожидался объект, получено {type(data).__name__}")
        _raise_if_kie_envelope(data)
        choices = data.get("choices")
        if not choices:
            raise KieAPIError(
                f"KIE: пустой choices в ответе: {raw_text[:400]}",
                retryable=True,
            )
        message = choices[0].get("message") or {}
        content = message.get("content")
        if content is None:
            raise KieAPIError("KIE: message.content пуст", retryable=True)
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(str(block["text"]))
                else:
                    parts.append(str(block))
            content = "".join(parts)
        return _SimpleResponse(content=str(content), raw=data)


def build_kie_chat_model(
    *,
    model: str | None = None,
    temperature: float | None = None,
) -> Any:
    """Клиент KIE с явной диагностикой daily limit / пустого data."""
    spec = resolve_model_spec(model)
    temp = spec.temperature if temperature is None else temperature
    return KieChatModel(
        model=spec.model_id,
        temperature=temp,
        api_key=kie_api_key(),
        base_url=kie_base_url_for(spec.model_id),
    )
