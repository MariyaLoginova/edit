"""Сквозные Pydantic-контракты пайплайна EDIT."""

from models.claim import Citation, ClaimCard, ClaimKind, ContrastPair, Scope
from models.dossier import (
    Dossier,
    ImageBuckets,
    ImageCandidate,
    SoftFactcheckResult,
    WebConfirmation,
    can_freeze,
)
from models.editorial import (
    CompressionReport,
    CritiqueReport,
    OpeningPick,
    OpeningVariant,
    RedAttack,
    RedAttackKind,
    RedCritique,
    RetellReport,
)
from models.idea import GenerationBrief, IdeaProbe, ProbeRegister
from models.learning import RolloutMetrics, ScoringWeights, WeightUpdate
from models.pipeline import ScoredClaim
from models.retention import BeatRisk, DropReason, RetentionReport
from models.scenario import Beat, BeatList, BeatRole, ScriptDraft, ScriptLine, ToneOfVoice
from models.shots import ShotImage, ShotList, ShotPacket
from models.source import SegmentStrategy, SourceMap, SourceSegment
from models.trace import TraceIssue, TraceReason, TraceReport

__all__ = [
    "Beat",
    "BeatList",
    "BeatRisk",
    "BeatRole",
    "Citation",
    "ClaimCard",
    "ClaimKind",
    "CompressionReport",
    "ContrastPair",
    "CritiqueReport",
    "Dossier",
    "DropReason",
    "GenerationBrief",
    "IdeaProbe",
    "ImageBuckets",
    "ImageCandidate",
    "OpeningPick",
    "OpeningVariant",
    "ProbeRegister",
    "RedAttack",
    "RedAttackKind",
    "RedCritique",
    "RetentionReport",
    "RetellReport",
    "RolloutMetrics",
    "Scope",
    "ScoredClaim",
    "ScoringWeights",
    "ScriptDraft",
    "ScriptLine",
    "SegmentStrategy",
    "ShotImage",
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
    "WeightUpdate",
    "can_freeze",
]
