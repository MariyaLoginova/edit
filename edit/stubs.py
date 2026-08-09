"""Ручные заглушки слоёв B/D.

B2 — человек выбирает тему. D — человек (пока) пишет сценарий из замороженного
досье. Слой C реализован узлами C1–C3.
"""

from __future__ import annotations

from models import ClaimCard, Dossier, ScriptDraft


def select_claim(
    claims: list[ClaimCard],
    selected_claim_id: str | None,
) -> ClaimCard | None:
    """B2-stub: человек передаёт claim_id; граф только резолвит карточку."""
    if not selected_claim_id:
        return None
    for card in claims:
        if card.claim_id == selected_claim_id:
            return card
    raise KeyError(f"selected_claim_id={selected_claim_id!r} нет среди claims")


def resolve_selected_claim(state_claims: list[ClaimCard], selected_claim_id: str | None) -> ClaimCard:
    card = select_claim(state_claims, selected_claim_id)
    if card is None:
        if len(state_claims) == 1:
            return state_claims[0]
        raise ValueError(
            "Нужен selected_claim_id (B2) или ровно одна карточка в claims"
        )
    return card


def require_manual_script(script: ScriptDraft | None) -> ScriptDraft:
    """D-stub: сценарий должен быть передан снаружи (написан человеком)."""
    if script is None:
        raise ValueError(
            "ScriptDraft задаётся вручную (слой D — заглушка до вехи 3). "
            "Передай script в state перед E1/E2."
        )
    if not script.lines:
        raise ValueError("ScriptDraft без lines/таймкодов — блокер для E1/E2")
    return script


def require_frozen_dossier(dossier: Dossier | None) -> Dossier:
    if dossier is None:
        raise ValueError("Нет досье — сначала C1–C3")
    if not dossier.frozen:
        raise ValueError("Досье не заморожено — C3 не пройден или freeze не вызван")
    return dossier
