"""Типизированный state EDIT (вехи 1–4)."""

from __future__ import annotations

from typing import Annotated, TypedDict

from models import (
    BeatList,
    ClaimCard,
    CompressionReport,
    Dossier,
    OpeningPick,
    RedCritique,
    RetentionReport,
    RetellReport,
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
    red_critique: RedCritique | None
    opening_pick: OpeningPick | None
    retell: RetellReport | None
    compression: CompressionReport | None
    blocked_for_production: bool
