"""F1 · Раскадровка: пачка картинок на фразу (отбор — человек на монтаже)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ShotImage(BaseModel):
    url: str
    title: str = ""
    description: str = ""
    query: str = ""
    soft_match: bool = False


class ShotPacket(BaseModel):
    """Пачка кандидатов на одну фразу. Слои отключает человек в монтажке."""

    t_start: float = Field(..., ge=0)
    t_end: float = Field(..., ge=0)
    phrase: str
    claim_id: str | None = None
    query: str = ""
    images: list[ShotImage] = Field(default_factory=list)

    @property
    def image_urls(self) -> list[str]:
        return [img.url for img in self.images]


class ShotList(BaseModel):
    script_id: str
    claim_id: str
    shots: list[ShotPacket]
    note: str = Field(
        "Отбор и права — вручную на монтаже, вне графа (ADR-002 / F1).",
    )
