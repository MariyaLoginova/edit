"""B1 · Скоринг ClaimCard по 5 осям; веса — из config (калибрует G1)."""

from __future__ import annotations

import re

from edit.config import scoring_weights
from models import ClaimCard, ClaimKind, ScoredClaim, ScoringWeights


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_axes(claim: ClaimCard) -> dict[str, float]:
    """Дешёвые эвристики (веха 5). Не LLM — чтобы G1 мог крутить веса часто."""
    surprise = _clamp01(len(claim.counter_expectation) / 120.0)
    # Конкретность факта/якоря, не качество картинки.
    vh = claim.visual_hint
    specificity = 0.4
    if re.search(r"\d{3,4}", vh):
        specificity += 0.3
    if re.search(r"[A-ZА-Я][a-zа-я]{2,}", vh):
        specificity += 0.2
    if len(vh) >= 20:
        specificity += 0.1
    specificity = _clamp01(specificity)

    causal_clarity = 0.85 if claim.kind is ClaimKind.causal else 0.65
    if claim.kind is ClaimKind.corrective:
        causal_clarity = 0.75
    if " потому что" in claim.claim.lower() or " из-за " in claim.claim.lower():
        causal_clarity = _clamp01(causal_clarity + 0.1)

    evidence = _clamp01(0.5 + len(claim.citation.quote) / 400.0)
    if claim.confidence >= 0.8:
        evidence = _clamp01(evidence + 0.15)

    # Shareability: неожиданный факт + конкретность + ясный поворот.
    shareability = _clamp01(0.4 * surprise + 0.35 * specificity + 0.25 * causal_clarity)
    return {
        "surprise": round(surprise, 4),
        "specificity": round(specificity, 4),
        "causal_clarity": round(causal_clarity, 4),
        "evidence": round(evidence, 4),
        "shareability": round(shareability, 4),
    }


def weighted_total(scores: dict[str, float], weights: ScoringWeights) -> float:
    w = weights.as_dict()
    num = sum(scores.get(k, 0.0) * float(w.get(k, 1.0)) for k in w)
    den = sum(abs(float(v)) for v in w.values()) or 1.0
    return round(num / den, 4)


def score_claims(
    claims: list[ClaimCard],
    *,
    weights: ScoringWeights | None = None,
) -> list[ScoredClaim]:
    w = weights or scoring_weights()
    scored = []
    for claim in claims:
        axes = score_axes(claim)
        scored.append(
            ScoredClaim(
                claim=claim,
                scores=axes,
                total=weighted_total(axes, w),
            )
        )
    scored.sort(key=lambda s: s.total, reverse=True)
    return [item.model_copy(update={"rank": i}) for i, item in enumerate(scored, start=1)]
