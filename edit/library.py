"""Загрузка редакционных библиотек (структуры, хуки, идеи, методики)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from edit.config import ROOT

NONE_ID = "none"
KNOWLEDGE_DIR = ROOT / "config" / "knowledge"


def _load_list(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError(f"{path}: ожидался список")
    return data


def load_knowledge_menu(name: str) -> str:
    """Короткое статичное меню знаний для system prompt (не RAG)."""
    path = KNOWLEDGE_DIR / f"{name}.txt"
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"пустой knowledge menu: {path}")
    return text


def compose_system_prompt(prompt_path: Path, knowledge_name: str | None = None) -> str:
    """Склеить базовый промпт + меню знаний. Меню — отдельные файлы для правок."""
    base = prompt_path.read_text(encoding="utf-8").strip()
    if not knowledge_name:
        return base
    menu = load_knowledge_menu(knowledge_name)
    return (
        f"{base}\n\n---\n"
        "ЗНАНИЯ (меню, не лекция — выбери пункт, не пересказывай блок)\n"
        f"{menu}"
    )


def load_stop_lists() -> dict[str, list[str]]:
    path = ROOT / "config" / "stop_lists.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: ожидался объект")
    return {
        "service_speech": [str(x) for x in (data.get("service_speech") or [])],
        "banned_phrases": [str(x) for x in (data.get("banned_phrases") or [])],
    }


def banned_speech_phrases() -> list[str]:
    lists = load_stop_lists()
    return [*lists["service_speech"], *lists["banned_phrases"]]


def load_idea_triggers() -> list[dict[str, Any]]:
    return _load_list(ROOT / "config" / "idea_triggers.yaml")


def load_hook_formulas() -> list[dict[str, Any]]:
    return _load_list(ROOT / "config" / "hook_formulas.yaml")


def load_open_second_triggers() -> list[dict[str, Any]]:
    return _load_list(ROOT / "config" / "open_second_triggers.yaml")


def idea_trigger_menu() -> list[dict[str, Any]]:
    menu = [
        {
            "id": item["id"],
            "name": item.get("name") or item["id"],
            "angle": item.get("angle") or "",
        }
        for item in load_idea_triggers()
    ]
    menu.append(
        {
            "id": NONE_ID,
            "name": "Без угла из банка идей",
            "angle": "Свободная линия от материала.",
        }
    )
    return menu


def normalize_library_id(raw: Any, *, known_ids: set[str]) -> str:
    if raw is None:
        return NONE_ID
    if isinstance(raw, dict):
        raw = raw.get("id") or raw.get("name") or ""
    text = str(raw).strip().lower()
    if not text or text in {"null", "none", "нет", "no", "-"}:
        return NONE_ID
    if text in known_ids or text == NONE_ID:
        return text
    return NONE_ID


def get_idea_trigger(trigger_id: str | None) -> dict[str, Any] | None:
    if not trigger_id or trigger_id == NONE_ID:
        return None
    for item in load_idea_triggers():
        if item.get("id") == trigger_id:
            return item
    return None
