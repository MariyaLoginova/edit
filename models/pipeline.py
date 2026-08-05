"""Сквозные сущности пайплайна (B) + реэкспорт сценария/шотов."""

from pydantic import BaseModel, Field

from models.claim import ClaimCard
from models.scenario import (  # noqa: F401
    Beat,
    BeatList,
    BeatRole,
    ScriptDraft,
    ScriptLine,
    ToneOfVoice,
)
from models.shots import ShotImage, ShotList, ShotPacket  # noqa: F401


class ScoredClaim(BaseModel):
    """B1 → после B2 замораживается выбор темы."""

    claim: ClaimCard
    scores: dict[str, float] = Field(default_factory=dict, description="Оси скоринга B1")
    total: float = 0.0
    rank: int | None = None
    selected: bool = False
