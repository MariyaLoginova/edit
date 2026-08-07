"""Тонкий адаптер KIE (OpenAI-compatible chat completions).

Паттерн как в CineFlow: ключ из env, модель/путь из config/llm.yaml,
узлы зовут LLM только через get_chat_model / этот модуль.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
LLM_CONFIG_PATH = ROOT / "config" / "llm.yaml"


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


def build_kie_chat_model(
    *,
    model: str | None = None,
    temperature: float | None = None,
) -> Any:
    """OpenAI-совместимый клиент на KIE endpoint выбранной модели."""
    from langchain_openai import ChatOpenAI

    spec = resolve_model_spec(model)
    temp = spec.temperature if temperature is None else temperature
    return ChatOpenAI(
        model=spec.model_id,
        temperature=temp,
        api_key=kie_api_key(),
        base_url=kie_base_url_for(spec.model_id),
    )
