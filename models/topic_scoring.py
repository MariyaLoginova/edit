"""Контракты B1 для ранжирования тем до производства."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TopicCandidate(BaseModel):
    """Кандидат из книги после добычи A2/ручной подготовки."""

    topic_id: str = Field(..., min_length=1, max_length=120)
    one_line: str = Field(..., min_length=1, max_length=400)
    naive_expectation: str = Field(..., min_length=1, max_length=300)
    source_conclusion_quote: str = Field(
        "", max_length=700, description="Дословный вывод автора; пусто → gate drop."
    )
    visual_examples: list[str] = Field(default_factory=list, max_length=12)
    format: Literal["excursion", "narrative", "argument"] = "excursion"
    source_locator: str = ""


class AxisScore(BaseModel):
    value: int = Field(..., ge=1, le=5)
    why: str = Field(..., min_length=1, max_length=200)


class ScoredTopic(BaseModel):
    topic_id: str
    gates_passed: bool
    gate_failures: list[str] = Field(default_factory=list)
    showable: AxisScore
    surprise: AxisScore
    recognizable: AxisScore
    social_currency: AxisScore
    arguable: AxisScore
    supersystem: AxisScore
    total: float
    verdict: Literal["produce", "bank", "drop"]
    one_line: str = Field(..., min_length=1, max_length=400)
