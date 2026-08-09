"""A1 → A2: сегментированный источник (SourceMap)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class SegmentStrategy(str, Enum):
    paragraph = "paragraph"  # по абзацам
    semantic = "semantic"  # склейка близких абзацев в смысловые блоки
    fixed_window = "fixed_window"  # окна по N токенов с перекрытием


class SourceSegment(BaseModel):
    segment_id: str = Field(..., description="Стабильный: {source_id}-{index:04d}")
    text: str = Field(..., min_length=1)
    ordinal: int = Field(0, ge=0, description="Порядок в источнике")
    heading: str | None = Field(None, description="Заголовок раздела/главы, если есть")
    token_estimate: int = Field(0, ge=0)
    locator: str = Field(
        "",
        description="Глава/раздел для Citation.locator (из heading или ordinal)",
    )

    @model_validator(mode="after")
    def _fill_defaults(self) -> SourceSegment:
        if not self.locator:
            object.__setattr__(
                self,
                "locator",
                self.heading or f"seg-{self.ordinal}",
            )
        if self.token_estimate <= 0:
            # грубая оценка: ~4 символа на токен
            object.__setattr__(self, "token_estimate", max(1, len(self.text) // 4))
        return self


class SourceMap(BaseModel):
    source_id: str = Field(..., description="Slug источника, напр. barbie-history-ch3")
    title: str = ""
    language: str = Field("ru", description="ru / en — влияет на A2; перевод на A1 не делаем")
    strategy: SegmentStrategy = SegmentStrategy.paragraph
    segments: list[SourceSegment]
