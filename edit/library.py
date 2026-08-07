"""Загрузка редакционных библиотек (структуры, хуки, идеи, методики)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from edit.config import ROOT

NONE_ID = "none"


def _load_list(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError(f"{path}: ожидался список")
    return data


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
