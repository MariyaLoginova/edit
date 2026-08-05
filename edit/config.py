"""Загрузка порогов из config/ — не хардкод в узлах."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from models import ScoringWeights

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS_PATH = ROOT / "config" / "thresholds.yaml"


@lru_cache(maxsize=1)
def load_thresholds() -> dict[str, Any]:
    with THRESHOLDS_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def clear_thresholds_cache() -> None:
    load_thresholds.cache_clear()


def dropoff_score_threshold() -> int:
    return int(load_thresholds().get("retention", {}).get("dropoff_score_threshold", 40))


def scoring_weights() -> ScoringWeights:
    raw = load_thresholds().get("scoring", {}).get("weights") or {}
    return ScoringWeights.model_validate(raw)


def persist_thresholds(data: dict[str, Any], *, path: Path | None = None) -> None:
    """Записать обновлённый конфиг (G1). Сбрасывает cache."""
    target = path or THRESHOLDS_PATH
    with target.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    clear_thresholds_cache()
