"""G1 · Пост-аналитик: метрики отвала/шеров → веса B1 и порог E2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edit.config import (
    THRESHOLDS_PATH,
    dropoff_score_threshold,
    load_thresholds,
    persist_thresholds,
    scoring_weights,
)
from models import RolloutMetrics, WeightUpdate


def analyze_rollouts(metrics: list[RolloutMetrics]) -> WeightUpdate:
    """Детерминированная калибровка (гипотеза до min_rollouts_for_calibration)."""
    base = scoring_weights()
    n = len(metrics)
    min_n = int(load_thresholds().get("learning", {}).get("min_rollouts_for_calibration", 15))
    hypothesis = n < min_n

    if n == 0:
        return WeightUpdate(
            scoring_weights=base,
            dropoff_score_threshold=None,
            n_rollouts_seen=0,
            hypothesis=True,
            notes="Нет метрик — веса не меняем.",
        )

    avg_watch = sum(m.avg_watch_pct for m in metrics) / n
    avg_drop3 = sum(m.dropoff_3s for m in metrics) / n
    avg_shares = sum(m.shares for m in metrics) / n
    avg_saves = sum(m.saves for m in metrics) / n

    w = base.model_copy()
    notes: list[str] = []

    if avg_drop3 > 0.35:
        w.surprise = round(min(2.0, w.surprise * 1.15), 4)
        w.specificity = round(min(2.0, w.specificity * 1.1), 4)
        notes.append("Высокий отвал 0–3с → подняли surprise/specificity.")

    if avg_watch < 0.45:
        w.causal_clarity = round(min(2.0, w.causal_clarity * 1.12), 4)
        w.evidence = round(min(2.0, w.evidence * 1.08), 4)
        notes.append("Низкий досмотр → подняли causal_clarity/evidence.")

    if avg_shares >= 50:
        w.shareability = round(min(2.0, w.shareability * 1.2), 4)
        notes.append("Много шеров → подняли shareability.")
    elif avg_shares < 5 and n >= 3:
        w.shareability = round(min(2.0, w.shareability * 1.05), 4)
        notes.append("Мало шеров → слегка подняли shareability.")

    if avg_saves >= 30:
        w.evidence = round(min(2.0, w.evidence * 1.1), 4)
        notes.append("Много сохранений → подняли evidence.")

    new_thr: int | None = None
    current = dropoff_score_threshold()
    paired = [m for m in metrics if m.e2_dropoff_score is not None]
    if paired:
        false_neg = [
            m for m in paired if (m.e2_dropoff_score or 0) < current and m.avg_watch_pct < 0.4
        ]
        if len(false_neg) >= max(1, len(paired) // 3):
            new_thr = max(20, current - 5)
            notes.append(
                f"E2 пропускал слабые ролики → предлагаем порог {new_thr} (было {current})."
            )

    if not notes:
        notes.append("Метрики в норме — веса без агрессивных сдвигов.")

    if hypothesis:
        notes.append(f"Гипотеза: n={n} < {min_n}; вердикты E2 = список подозрений.")

    return WeightUpdate(
        scoring_weights=w,
        dropoff_score_threshold=new_thr,
        n_rollouts_seen=n,
        hypothesis=hypothesis,
        notes=" ".join(notes)[:500],
    )


def apply_weight_update(
    update: WeightUpdate,
    *,
    path: Path | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Слить WeightUpdate в конфиг; при persist=True записать YAML."""
    data = dict(load_thresholds())
    scoring = dict(data.get("scoring") or {})
    scoring["weights"] = update.scoring_weights.as_dict()
    data["scoring"] = scoring
    if update.dropoff_score_threshold is not None:
        retention = dict(data.get("retention") or {})
        retention["dropoff_score_threshold"] = update.dropoff_score_threshold
        data["retention"] = retention
    if persist:
        persist_thresholds(data, path=path or THRESHOLDS_PATH)
    return data
