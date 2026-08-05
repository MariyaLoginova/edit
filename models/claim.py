"""EDIT-A2 · ClaimCard — единица добычи (причинный тезис)."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ClaimKind(str, Enum):
    causal = "causal"  # почему визуал такой (ЦЕЛЕВОЙ тип)
    corrective = "corrective"  # распространённое заблуждение опровергается
    origin = "origin"  # откуда взялась форма/приём
    # descriptive НЕ включён намеренно: "что изображено" — не наш жанр


class Citation(BaseModel):
    locator: str = Field(..., description="Глава/раздел/страница внутри источника")
    quote: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Дословная цитата из источника, подтверждающая claim. НЕ пересказ.",
    )


class Scope(BaseModel):
    period: str | None = Field(None, description="Год/эпоха, к которым относится тезис")
    region: str | None = Field(None, description="Гео/культурный контекст")
    author_or_work: str | None = Field(
        None, description="Автор, студия, бренд, конкретное произведение"
    )


class ClaimCard(BaseModel):
    claim_id: str = Field(..., description="Стабильный slug, напр. bauhaus-sans-serif-cost")
    kind: ClaimKind

    claim: str = Field(
        ...,
        min_length=1,
        max_length=240,
        description="ОДНО утверждение о причине визуального решения. Одно, не составное.",
    )
    counter_expectation: str = Field(
        ...,
        min_length=1,
        max_length=240,
        description=(
            "Что аудитория (дизайнеры/художники 20-40) по умолчанию думает об этом. "
            "Именно контраст claim vs counter_expectation даёт крючок."
        ),
    )
    visual_hint: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description=(
            "Конкретный объект/кадр, который ДОКАЗЫВАЕТ claim визуально. "
            "Не абстракция ('модернизм'), а вещь ('обложка Vogue 1926, шрифт X')."
        ),
    )

    citation: Citation
    scope: Scope

    source_segment_id: str = Field(
        ..., description="ID сегмента из source_map, откуда извлечён тезис"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Уверенность майнера, что тезис реально присутствует в сегменте",
    )

    @field_validator("claim")
    @classmethod
    def _single_claim(cls, v: str) -> str:
        # «и» в русском слишком частотно — не режем. Ловим явные склейки.
        # Жёсткая проверка составности — на скоринге B1.
        lowered = v.lower()
        for sep in ["; ", " а также ", " также ", " и при этом ", " и одновременно "]:
            if sep in lowered:
                raise ValueError(
                    f"claim выглядит составным (найдено '{sep.strip()}'). "
                    "Разбей на отдельные карточки."
                )
        return v
