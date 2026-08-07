"""Типизированный state EDIT (FIX-4)."""

from __future__ import annotations

from typing import Annotated, TypedDict

from models import (
    BeatList,
    ClaimCard,
    CompressionReport,
    CritiqueReport,
    Dossier,
    IdeaProbe,
    HookDraft,
    MonologueCheck,
    MonologueDraft,
    ResearchPack,
    OpeningPick,
    RedCritique,
    RetentionReport,
    RetellReport,
    RolloutMetrics,
    ScoredClaim,
    ScriptDraft,
    ShotList,
    SourceMap,
    StoryBrief,
    TraceReport,
    WeightUpdate,
)


def _merge_claims(left: list[ClaimCard], right: list[ClaimCard]) -> list[ClaimCard]:
    by_id = {c.claim_id: c for c in left}
    for c in right:
        by_id[c.claim_id] = c
    return list(by_id.values())


class EditState(TypedDict, total=False):
    source_map: SourceMap
    primary_text: str
    claims: Annotated[list[ClaimCard], _merge_claims]
    scored_claims: list[ScoredClaim]
    rejected_notes: list[str]
    selected_claim_id: str | None
    dossier: Dossier | None
    beats: BeatList | None  # legacy; D1 удалён из графа
    script: ScriptDraft | None
    story_brief: StoryBrief | None
    hook_draft: HookDraft | None
    monologue: MonologueDraft | None
    monologue_check: MonologueCheck | None
    research_pack: ResearchPack | None
    trace: TraceReport | None
    critique: CritiqueReport | None
    # legacy поля (старые узлы/тесты) — не пишутся новым графом
    retention: RetentionReport | None
    red_critique: RedCritique | None
    opening_pick: OpeningPick | None
    retell: RetellReport | None
    compression: CompressionReport | None
    idea_probe: IdeaProbe | None
    idea_probe_included: bool | None
    shot_list: ShotList | None
    rollout_metrics: list[RolloutMetrics]
    weight_update: WeightUpdate | None
    blocked_for_production: bool
