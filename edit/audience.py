"""Ручной контекст аудитории для личного редакционного контура."""

from __future__ import annotations

from pathlib import Path

from edit.config import ROOT

AUDIENCE_PATH = ROOT / "config" / "audience.md"


def load_audience() -> str:
    """Возвращает ручной файл; незаполненные поля явно видны агенту."""
    return AUDIENCE_PATH.read_text(encoding="utf-8").strip()
