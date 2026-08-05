"""Сквозные сущности пайплайна (B/F) + реэкспорт сценария."""

from pydantic import BaseModel, Field

from models.claim import ClaimCard
from models.scenario import (  # noqa: F401 — стабильный импорт-путь
    Beat,
    BeatList,
    BeatRole,
    ScriptDraft,
    ScriptLine,
    ToneOfVoice,
)


class ScoredClaim(BaseModel):
    """B1 → после B2 замораживается выбор темы."""

    claim: ClaimCard
    scores: dict[str, float] = Field(default_factory=dict, description="Оси скоринга B1")
    rank: int | None = None
    selected: bool = False


class ShotPacket(BaseModel):
    """F1: пачка картинок на фразу; отбор слоёв — человек на монтаже."""

    t_start: float = Field(..., ge=0)
    t_end: float = Field(..., ge=0)
    phrase: str
    claim_id: str | None = None
    image_urls: list[str] = Field(default_factory=list)


class ShotList(BaseModel):
    script_id: str
    shots: list[ShotPacket]
