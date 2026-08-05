"""Сквозные Pydantic-контракты пайплайна EDIT.

Порядок — снизу вверх по зависимостям (см. README §5).
Контракты A2 / E2 / E7 — как в тикетах, без изменений.
"""

from models.claim import Citation, ClaimCard, ClaimKind, Scope
from models.dossier import (
    Dossier,
    ImageCandidate,
    SoftFactcheckResult,
    WebConfirmation,
)
from models.idea import GenerationBrief, IdeaProbe, ProbeRegister
from models.pipeline import (
    Beat,
    BeatList,
    ScoredClaim,
    ScriptDraft,
    ScriptLine,
    ShotList,
    ShotPacket,
)
from models.retention import BeatRisk, DropReason, RetentionReport
from models.source import SourceMap, SourceSegment
from models.trace import TraceIssue, TraceReason, TraceReport

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
    "ImageCandidate",
    "ProbeRegister",
    "RetentionReport",
    "Scope",
    "ScoredClaim",
    "ScriptDraft",
    "ScriptLine",
    "ShotList",
    "ShotPacket",
    "SoftFactcheckResult",
    "SourceMap",
    "SourceSegment",
    "TraceIssue",
    "TraceReason",
    "TraceReport",
    "WebConfirmation",
]
