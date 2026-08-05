"""Сквозные Pydantic-контракты пайплайна EDIT."""

from models.claim import Citation, ClaimCard, ClaimKind, Scope
from models.dossier import (
    Dossier,
    ImageCandidate,
    SoftFactcheckResult,
    WebConfirmation,
)
from models.idea import GenerationBrief, IdeaProbe, ProbeRegister
from models.pipeline import ScoredClaim, ShotList, ShotPacket
from models.retention import BeatRisk, DropReason, RetentionReport
from models.scenario import Beat, BeatList, BeatRole, ScriptDraft, ScriptLine, ToneOfVoice
from models.source import SourceMap, SourceSegment
from models.trace import TraceIssue, TraceReason, TraceReport

__all__ = [
    "Beat",
    "BeatList",
    "BeatRisk",
    "BeatRole",
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
    "ToneOfVoice",
    "TraceIssue",
    "TraceReason",
    "TraceReport",
    "WebConfirmation",
]
