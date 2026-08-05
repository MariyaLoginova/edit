"""Слой C: материал и заморозка досье (ADR-002 / веха 2)."""

from __future__ import annotations

from datetime import datetime, timezone

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
        "", description="Краткая выжимка собранного материала (C1), не новые факты от сценариста"
    )
    web_confirmations: list[WebConfirmation] = Field(default_factory=list)
    image_candidates: list[ImageCandidate] = Field(default_factory=list)
    soft_factcheck: SoftFactcheckResult | None = None
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

    def freeze(self) -> Dossier:
        """Заморозка SSOT. Только после успешного C3."""
        if self.frozen:
            return self
        if self.soft_factcheck is None:
            raise ValueError("нельзя заморозить досье без C3 soft_factcheck")
        if not self.soft_factcheck.ok:
            raise ValueError(
                "нельзя заморозить досье: soft_factcheck.ok=False "
                f"({self.soft_factcheck.invented_items})"
            )
        return self.model_copy(
            update={
                "frozen": True,
                "frozen_at": datetime.now(timezone.utc).isoformat(),
            }
        )
