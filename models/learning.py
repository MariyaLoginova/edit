"""G1 · Пост-аналитик и калибровка весов B1 / порога E2."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RolloutMetrics(BaseModel):
    """Метрики выпущенного ролика (вход G1). До ~15–20 штук — шумно."""

    script_id: str
    claim_id: str
    avg_watch_pct: float = Field(..., ge=0.0, le=1.0, description="Доля досмотра 0..1")
    dropoff_3s: float = Field(
        ..., ge=0.0, le=1.0, description="Доля отвала в первые 3 сек"
    )
    shares: int = Field(..., ge=0)
    saves: int = Field(..., ge=0)
    e2_dropoff_score: int | None = Field(
        None, ge=0, le=100, description="Предсказание E2 на этапе редакции"
    )


class ScoringWeights(BaseModel):
    """5 осей B1 — в конфиг, калибруется G1."""

    surprise: float = 1.0
    visuality: float = 1.0
    causal_clarity: float = 1.0
    evidence: float = 1.0
    shareability: float = 1.0

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()


class WeightUpdate(BaseModel):
    """Выход G1: новые веса/порог. hypothesis=True пока мало роликов."""

    scoring_weights: ScoringWeights
    dropoff_score_threshold: int | None = Field(
        None, description="Предлагаемый порог E2; None = не трогать"
    )
    n_rollouts_seen: int = Field(..., ge=0)
    hypothesis: bool = True
    notes: str = Field(..., max_length=500)
