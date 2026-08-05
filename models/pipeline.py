"""Сквозные сущности пайплайна кроме ClaimCard / Dossier / Retention / Idea."""

from pydantic import BaseModel, Field

from models.claim import ClaimCard


class ScoredClaim(BaseModel):
    """B1 → после B2 замораживается выбор темы."""

    claim: ClaimCard
    scores: dict[str, float] = Field(default_factory=dict, description="Оси скоринга B1")
    rank: int | None = None
    selected: bool = False


class Beat(BaseModel):
    """Элемент BeatList (D1). Таймкоды обязательны — блокер для E2."""

    beat_id: str
    t_start: float = Field(..., ge=0)
    t_end: float = Field(..., ge=0)
    role: str = Field(..., description="Роль бита в формуле ролика")
    claim_id: str | None = None
    notes: str = ""


class BeatList(BaseModel):
    script_id: str
    beats: list[Beat]
    duration_sec: float = Field(..., ge=0)


class ScriptLine(BaseModel):
    """Фраза сценария с привязкой ко времени и claim_id (трассируемость E1)."""

    t_start: float = Field(..., ge=0)
    t_end: float = Field(..., ge=0)
    text: str = Field(..., min_length=1)
    claim_id: str | None = Field(
        None,
        description="None допустим только для связок/маркеров мнения; факты — обязателен",
    )


class ScriptDraft(BaseModel):
    """D2/D3 → вход E1–E6. Без таймкодов E2 не работает."""

    script_id: str
    claim_id: str
    lines: list[ScriptLine]
    duration_sec: float = Field(..., ge=0)


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
