"""Слой E3–E6: редактура после E1/E2 (веха 4)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from models.scenario import ScriptDraft


class RedAttackKind(str, Enum):
    banal = "banal"  # банально / и так все знают
    unsupported = "unsupported"  # не следует из досье/посылки
    non_sequitur = "non_sequitur"  # скачок логики
    second_thesis = "second_thesis"  # расползание во второй сюжет
    overclaim = "overclaim"  # завышенная атрибуция/причина
    vague = "vague"  # абстракция без объекта


class RedAttack(BaseModel):
    kind: RedAttackKind
    quote: str = Field(..., min_length=1)
    attack: str = Field(..., min_length=1, description="Враждебный разнос, не правка")
    severity: int = Field(..., ge=1, le=5)


class RedCritique(BaseModel):
    """E3 · Красный критик — бьёт по СОДЕРЖАНИЮ, не по динамике (это E2)."""

    script_id: str
    attacks: list[RedAttack] = Field(default_factory=list)
    severity_max: int = Field(..., ge=1, le=5)
    passes: bool = Field(..., description="False если есть attack с severity>=4")
    summary: str = Field(..., max_length=400)


class OpeningVariant(BaseModel):
    text: str = Field(..., min_length=1, max_length=280, description="Озвучка первых ~3 сек")
    rationale: str = Field(..., min_length=1, max_length=240)
    hook_strength: int = Field(..., ge=1, le=5)


class OpeningPick(BaseModel):
    """E4 · Перебор открытий: 5–8 вариантов, выбран один, script обновлён."""

    script_id: str
    variants: list[OpeningVariant]
    chosen_index: int = Field(..., ge=0)
    chosen_text: str = ""
    script: ScriptDraft

    @model_validator(mode="after")
    def _choose(self) -> OpeningPick:
        if len(self.variants) < 5:
            raise ValueError("E4: нужно ≥5 вариантов открытия")
        if len(self.variants) > 8:
            raise ValueError("E4: не больше 8 вариантов")
        if self.chosen_index >= len(self.variants):
            raise ValueError("E4: chosen_index вне диапазона")
        chosen = self.variants[self.chosen_index]
        return self.model_copy(update={"chosen_text": chosen.text})


class RetellReport(BaseModel):
    """E5 · Пересказ одним предложением → проверка коды."""

    script_id: str
    retell: str = Field(..., min_length=1, max_length=280)
    coda_quote: str = Field(..., description="Фактическая кода из сценария")
    coda_is_quotable: bool
    retell_matches_coda: bool
    passes: bool
    fix_hint: str = Field("", max_length=240)
    summary: str = Field(..., max_length=400)


class CompressionReport(BaseModel):
    """E6 · Сжатие −20–25% длины без потери смысла/claim_id."""

    script_id: str
    original_chars: int = Field(..., ge=0)
    compressed_chars: int = Field(..., ge=0)
    reduction_ratio: float = Field(..., ge=0.0, le=1.0)
    script: ScriptDraft
    passes: bool
    summary: str = Field(..., max_length=400)
