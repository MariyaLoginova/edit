"""Загрузка порогов из config/ — не хардкод в узлах."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS_PATH = ROOT / "config" / "thresholds.yaml"


@lru_cache(maxsize=1)
def load_thresholds() -> dict[str, Any]:
    with THRESHOLDS_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def dropoff_score_threshold() -> int:
    return int(load_thresholds().get("retention", {}).get("dropoff_score_threshold", 40))
