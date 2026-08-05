"""Слой C: материал и заморозка досье (ADR-002 / FIX-2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.claim import ClaimCard


class WebConfirmation(BaseModel):
    """Лёгкое веб-подтверждение тезиса (C1). Не SAFE, не voting."""

    url: str
    title: str = ""
    snippet: str = ""
    query: str = ""
    supports_claim: bool = Field(
        True, description="Мягкая оценка: сниппет выглядит подтверждающим тезис"
    )


class ImageCandidate(BaseModel):
    """Картинка из веб-поиска (C2). Отбор и права — вручную на монтаже."""

    url: str
    title: str = ""
    description: str = ""
    query: str
    soft_match: bool = Field(
        ...,
        description="True, если описание/метаданные ≈ запросу (токены пересекаются)",
    )
    for_state: Literal["a", "b"] | None = Field(
        None, description="К какому состоянию contrast_pair привязана картинка"
    )


class ImageBuckets(BaseModel):
    """Картинки под A/B (FIX-2). Пустой список ≠ сбой поиска."""

    for_state_a: list[ImageCandidate] = Field(default_factory=list)
    for_state_b: list[ImageCandidate] = Field(default_factory=list)
    search_status: Literal["ok", "empty", "unavailable"] = "ok"
    search_error: str | None = None

    def all_images(self) -> list[ImageCandidate]:
        return [*self.for_state_a, *self.for_state_b]


class SoftFactcheckResult(BaseModel):
    """C3: одна LLM-развилка «нет ли выдуманных дат/имён/атрибуций»."""

    ok: bool
    invented_items: list[str] = Field(
        default_factory=list,
        description="Подозрительные даты/имена/атрибуции, похожие на выдумку",
    )
    rationale: str = Field("", max_length=500)


class Dossier(BaseModel):
    """C1–C3. После C3 — SSOT, иммутабелен (инвариант 1)."""

    model_config = ConfigDict(validate_assignment=True)

    claim_id: str
    claim: ClaimCard
    material_notes: str = Field(
        "", description="Краткая выжимка собранного материала (C1)"
    )
    web_confirmations: list[WebConfirmation] = Field(default_factory=list)
    image_candidates: ImageBuckets = Field(default_factory=ImageBuckets)
    soft_factcheck: SoftFactcheckResult | None = None
    freeze_blockers: list[str] = Field(
        default_factory=list,
        description="Причины, почему can_freeze=false (FIX-2)",
    )
    frozen: bool = False
    frozen_at: str | None = None

    @model_validator(mode="after")
    def _claim_id_matches(self) -> Dossier:
        if self.claim_id != self.claim.claim_id:
            raise ValueError("dossier.claim_id должен совпадать с claim.claim_id")
        return self

    def ensure_mutable(self) -> None:
        if self.frozen:
            raise RuntimeError(
                "Dossier заморожен после C3 — мутация запрещена (инвариант 1)"
            )

    def freeze(self, *, require_images: bool = True) -> Dossier:
        """Заморозка SSOT. Только после успешного C3 + can_freeze."""
        if self.frozen:
            return self
        if self.soft_factcheck is None:
            raise ValueError("нельзя заморозить досье без C3 soft_factcheck")
        if not self.soft_factcheck.ok:
            raise ValueError(
                "нельзя заморозить досье: soft_factcheck.ok=False "
                f"({self.soft_factcheck.invented_items})"
            )
        ok, problems = can_freeze(self, require_images=require_images)
        if not ok:
            raise ValueError(
                "нельзя заморозить досье — неполный материал: " + "; ".join(problems)
            )
        return self.model_copy(
            update={
                "frozen": True,
                "frozen_at": datetime.now(timezone.utc).isoformat(),
                "freeze_blockers": [],
            }
        )


def can_freeze(
    d: Dossier,
    *,
    min_images_per_state: int = 3,
    require_images: bool = True,
) -> tuple[bool, list[str]]:
    """Гейт материала: факты обязательны; картинки — только для visual/F1 режима."""
    problems: list[str] = []
    if not (d.material_notes or "").strip():
        problems.append("material_notes пусто")
    if not d.web_confirmations:
        problems.append("нет ни одного web_confirmation")
    if require_images:
        buckets = d.image_candidates
        if buckets.search_status == "unavailable":
            problems.append(
                f"поиск картинок не отработал: {buckets.search_error or 'unknown'}"
            )
        if len(buckets.for_state_a) < min_images_per_state:
            problems.append(
                f"нет картинок под state_a "
                f"({len(buckets.for_state_a)}<{min_images_per_state})"
            )
        if len(buckets.for_state_b) < min_images_per_state:
            problems.append(
                f"нет картинок под state_b "
                f"({len(buckets.for_state_b)}<{min_images_per_state})"
            )
    return (not problems, problems)
