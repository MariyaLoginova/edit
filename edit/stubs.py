"""Ручные заглушки слоёв B/C/D для вехи 1 (вертикальный срез).

Тема выбирается человеком (B2), материал и сценарий пишутся руками,
затем прогоняются через E2. Здесь — только прокидка уже готовых артефактов.
"""

from __future__ import annotations

from models import ClaimCard, ScriptDraft


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


def require_manual_script(script: ScriptDraft | None) -> ScriptDraft:
    """D-stub: сценарий должен быть передан снаружи (написан человеком)."""
    if script is None:
        raise ValueError(
            "Веха 1: ScriptDraft задаётся вручную (слой D — заглушка). "
            "Передай script в state перед E2."
        )
    if not script.lines:
        raise ValueError("ScriptDraft без lines/таймкодов — блокер для E2")
    return script
