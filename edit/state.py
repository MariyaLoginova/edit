"""Типизированный state вертикального среза EDIT (веха 1)."""

from __future__ import annotations

from typing import Annotated, TypedDict

from models import ClaimCard, RetentionReport, ScriptDraft, SourceMap


def _merge_claims(left: list[ClaimCard], right: list[ClaimCard]) -> list[ClaimCard]:
    by_id = {c.claim_id: c for c in left}
    for c in right:
        by_id[c.claim_id] = c
    return list(by_id.values())


class EditState(TypedDict, total=False):
    source_map: SourceMap
    claims: Annotated[list[ClaimCard], _merge_claims]
    rejected_notes: list[str]
    selected_claim_id: str | None
    # ручной сценарий (заглушка D) — вход для E2
    script: ScriptDraft | None
    retention: RetentionReport | None
    # True, если E2 блокирует выход в F
    blocked_for_production: bool
