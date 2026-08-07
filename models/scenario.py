"""Слой D: структура и сценарий (веха 3 / FIX-3)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from models.claim import ClaimCard


class BeatRole(str, Enum):
    """Норма канала (FIX-3): хук → ложное объяснение → A/B → механизм → формула."""

    hook_evidence = "hook_evidence"  # object_anchor
    false_explanation = "false_explanation"  # counter_expectation
    contrast_ab = "contrast_ab"  # contrast_pair
    mechanism = "mechanism"  # mechanism_term + explain
    coda = "coda"  # формула


class Beat(BaseModel):
    """Элемент BeatList (D1). Таймкоды обязательны — блокер для E2."""

    beat_id: str
    t_start: float = Field(..., ge=0)
    t_end: float = Field(..., ge=0)
    role: BeatRole
    claim_id: str | None = None
    intent: str = Field(
        "",
        description="Что должен сделать бит (не готовая проза)",
    )

    @model_validator(mode="after")
    def _time_order(self) -> Beat:
        if self.t_end <= self.t_start:
            raise ValueError(f"beat {self.beat_id}: t_end должен быть > t_start")
        return self


class BeatList(BaseModel):
    script_id: str
    claim_id: str
    beats: list[Beat]
    duration_sec: float = Field(..., ge=0)

    @model_validator(mode="after")
    def _require_timecodes_and_coverage(self) -> BeatList:
        if not self.beats:
            raise ValueError("BeatList пуст — D1 обязан отдать структуру с таймкодами")
        ordered = sorted(self.beats, key=lambda b: b.t_start)
        if ordered[0].t_start > 0.05:
            raise ValueError("первый бит должен начинаться с t_start≈0 (блокер E2)")
        prev_end = ordered[0].t_start
        for b in ordered:
            if b.t_start < prev_end - 0.05:
                raise ValueError(f"перекрытие битов около {b.beat_id}")
            if b.t_start > prev_end + 0.51:
                raise ValueError(f"разрыв таймкодов перед {b.beat_id} — блокер для E2")
            prev_end = b.t_end
        if abs(self.duration_sec - ordered[-1].t_end) > 0.51:
            raise ValueError("duration_sec должен совпадать с концом последнего бита")
        roles = {b.role for b in self.beats}
        required = {
            BeatRole.hook_evidence,
            BeatRole.false_explanation,
            BeatRole.contrast_ab,
            BeatRole.mechanism,
            BeatRole.coda,
        }
        missing = required - roles
        if missing:
            raise ValueError(f"в BeatList не хватает ролей: {sorted(r.value for r in missing)}")
        # механизм/формула не раньше 55% длительности
        mech = next(b for b in ordered if b.role == BeatRole.mechanism)
        if mech.t_start < self.duration_sec * 0.55 - 0.5:
            raise ValueError(
                f"mechanism слишком рано ({mech.t_start}s < 55% от {self.duration_sec}s)"
            )
        return self


class ScriptLine(BaseModel):
    t_start: float = Field(..., ge=0)
    t_end: float = Field(..., ge=0)
    text: str = Field(..., min_length=1)
    claim_id: str | None = Field(
        None, description="Если line несёт факт — обязателен claim_id из досье"
    )
    beat_id: str | None = None

    @model_validator(mode="after")
    def _time_order(self) -> ScriptLine:
        if self.t_end <= self.t_start:
            raise ValueError("ScriptLine: t_end должен быть > t_start")
        return self


class ScriptDraft(BaseModel):
    script_id: str
    claim_id: str
    lines: list[ScriptLine]
    duration_sec: float = Field(..., ge=0)
    tov_applied: bool = False

    @model_validator(mode="after")
    def _non_empty_and_timecodes(self) -> ScriptDraft:
        if not self.lines:
            raise ValueError("ScriptDraft.lines пуст")
        ordered = sorted(self.lines, key=lambda ln: ln.t_start)
        if ordered[0].t_start > 0.05:
            raise ValueError("первая реплика должна начинаться с t_start≈0")
        prev_end = ordered[0].t_start
        for ln in ordered:
            if ln.t_start < prev_end - 0.05:
                raise ValueError(f"перекрытие реплик около {ln.t_start}s")
            if ln.t_start > prev_end + 0.51:
                raise ValueError(f"разрыв таймкодов перед {ln.t_start}s")
            prev_end = ln.t_end
        if abs(self.duration_sec - ordered[-1].t_end) > 0.51:
            raise ValueError("duration_sec должен совпадать с концом последней реплики")
        return self


class ToneOfVoice(BaseModel):
    """Словарь персонажа (D3) — не факты."""

    name: str = "visual-culture-host"
    principles: list[str] = Field(default_factory=list)
    prefer: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    sample_phrases: list[str] = Field(default_factory=list)


# re-export for type checkers that imported ClaimCard from here historically
__all__ = [
    "Beat",
    "BeatList",
    "BeatRole",
    "ClaimCard",
    "ScriptDraft",
    "ScriptLine",
    "ToneOfVoice",
]
