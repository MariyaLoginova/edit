"""Библиотека структур рилсов для E-editor → D2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from edit.config import ROOT

STRUCTURES_PATH = ROOT / "config" / "reel_structures.yaml"
NONE_ID = "none"


def load_structures() -> list[dict[str, Any]]:
    data = yaml.safe_load(STRUCTURES_PATH.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError("reel_structures.yaml: ожидался список")
    return data


def structure_menu() -> list[dict[str, Any]]:
    """Короткое меню для E-editor: без full_example."""
    menu = []
    for item in load_structures():
        menu.append(
            {
                "id": item["id"],
                "name": item.get("name") or item["id"],
                "suits": item.get("suits") or "",
                "beats": item.get("beats") or [],
            }
        )
    menu.append(
        {
            "id": NONE_ID,
            "name": "Без структуры из библиотеки",
            "suits": "Ни одна не близка — работай свободной научпоп-линией.",
            "beats": [],
        }
    )
    return menu


def get_structure(structure_id: str | None) -> dict[str, Any] | None:
    if not structure_id or structure_id == NONE_ID:
        return None
    for item in load_structures():
        if item.get("id") == structure_id:
            return item
    return None


def normalize_structure_id(raw: Any) -> str:
    if raw is None:
        return NONE_ID
    if isinstance(raw, dict):
        raw = raw.get("id") or raw.get("structure_id") or raw.get("name") or ""
    text = str(raw).strip().lower()
    if not text or text in {"null", "none", "нет", "no", "-"}:
        return NONE_ID
    known = {item["id"] for item in load_structures()} | {NONE_ID}
    if text in known:
        return text
    # иногда модель возвращает имя
    for item in load_structures():
        name = str(item.get("name") or "").strip().lower()
        if text == name or text in name:
            return str(item["id"])
    return NONE_ID
