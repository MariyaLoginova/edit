"""A1 → A2: сегментированный источник (source_map).

Формат A1 ещё открыт (README §8); для вехи 1 — смысловые сегменты с id и текстом.
"""

from pydantic import BaseModel, Field


class SourceSegment(BaseModel):
    segment_id: str = Field(..., description="Стабильный id сегмента внутри source_map")
    locator: str = Field(..., description="Глава/раздел/страницы — уходит в Citation.locator")
    text: str = Field(..., min_length=1, description="Полный текст сегмента")


class SourceMap(BaseModel):
    source_id: str
    title: str = ""
    segments: list[SourceSegment]
