"""Типизированный state EDIT (вехи 1–3)."""

from __future__ import annotations

from typing import Annotated, TypedDict

from models import (
    BeatList,
    ClaimCard,
    Dossier,
    RetentionReport,
    ScriptDraft,
    SourceMap,
    TraceReport,
)


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
    dossier: Dossier | None
    beats: BeatList | None
    script: ScriptDraft | None
    trace: TraceReport | None
    retention: RetentionReport | None
    blocked_for_production: bool
