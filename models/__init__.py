"""Сквозные Pydantic-контракты пайплайна EDIT.

Порядок — снизу вверх по зависимостям (см. README §5).
Контракты A2 / E2 / E7 — как в тикетах, без изменений.
"""

from models.claim import Citation, ClaimCard, ClaimKind, Scope
from models.idea import GenerationBrief, IdeaProbe, ProbeRegister
from models.pipeline import (
    Beat,
    BeatList,
    Dossier,
    ScoredClaim,
    ScriptDraft,
    ScriptLine,
    ShotList,
    ShotPacket,
)
from models.retention import BeatRisk, DropReason, RetentionReport

__all__ = [
    "Beat",
    "BeatList",
    "BeatRisk",
    "Citation",
    "ClaimCard",
    "ClaimKind",
    "Dossier",
    "DropReason",
    "GenerationBrief",
    "IdeaProbe",
    "ProbeRegister",
    "RetentionReport",
    "Scope",
    "ScoredClaim",
    "ScriptDraft",
    "ScriptLine",
    "ShotList",
    "ShotPacket",
]
