"""Контракты личного редакционного контура (EDIT-FORM)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class EndingType(str, Enum):
    formula = "formula"
    reactive = "reactive"


class ReelFormat(str, Enum):
    """Экскурсия — по умолчанию; аргумент — исключение."""

    excursion = "excursion"
    argument = "argument"


class ProofItem(BaseModel):
    point: str = Field(..., min_length=1, max_length=300)
    source_quote: str = Field(
        ...,
        min_length=1,
        max_length=700,
        description="Дословная непрерывная цитата из первичного текста.",
    )


class Exhibit(BaseModel):
    """Единица экскурсии: назвать + что видно. Без объяснения смысла."""

    name: str = Field(..., min_length=1, max_length=120)
    what_to_see: str = Field(..., min_length=1, max_length=280)
    note: str | None = Field(None, max_length=200)
    source_quote: str | None = Field(None, max_length=700)


class Conclusion(BaseModel):
    """Вывод из источника — не сочинение конвейера."""

    source_quote: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Дословная короткая цитата-опора; не для озвучки.",
    )
    plain: str = Field(
        ...,
        min_length=1,
        max_length=400,
        description="То же живыми словами — для озвучки в конце.",
    )


class VisualReference(BaseModel):
    """Найденный внешний референс к одному кадру плана."""

    url: str = Field(..., min_length=1)
    title: str = ""
    description: str = ""


class VisualPlanBeat(BaseModel):
    """Секция сценария: речь D2 строится по этому плану, монтаж — по visual_plan."""

    beat_id: str = Field(..., min_length=1, max_length=80)
    t_start: float = Field(..., ge=0)
    t_end: float = Field(..., gt=0)
    exhibit_name: str = Field(..., min_length=1, max_length=160)
    narration_intent: str = Field(..., min_length=1, max_length=400)
    what_to_show: str = Field(..., min_length=1, max_length=500)
    image_query: str = Field(..., min_length=1, max_length=300)
    image_references: list[VisualReference] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def _time_order(self) -> VisualPlanBeat:
        if self.t_end <= self.t_start:
            raise ValueError(f"{self.beat_id}: t_end должен быть больше t_start")
        return self


class VisualScenarioPlan(BaseModel):
    """Монтажный сценарий между E-редактором и D2."""

    claim_id: str
    format: ReelFormat
    duration_sec: float = Field(..., ge=180, le=300)
    opening_intent: str = Field(..., min_length=1, max_length=400)
    beats: list[VisualPlanBeat] = Field(default_factory=list)
    image_search_status: Literal["ok", "empty", "unavailable"] = "empty"
    image_search_error: str | None = None

    @model_validator(mode="after")
    def _timeline_matches_format(self) -> VisualScenarioPlan:
        n = len(self.beats)
        if self.format == ReelFormat.excursion and not 6 <= n <= 10:
            raise ValueError(f"excursion visual plan: нужно 6–10 битов, получено {n}")
        if self.format == ReelFormat.argument and n < 4:
            raise ValueError("argument visual plan: нужно минимум 4 бита")
        if not self.beats:
            return self
        ordered = sorted(self.beats, key=lambda b: b.t_start)
        if ordered[0].t_start > 0.5:
            raise ValueError("visual plan: первый бит должен начинаться около 0")
        previous_end = ordered[0].t_start
        for beat in ordered:
            if beat.t_start < previous_end - 0.5:
                raise ValueError(f"visual plan: перекрытие около {beat.beat_id}")
            if beat.t_start > previous_end + 1.0:
                raise ValueError(f"visual plan: разрыв перед {beat.beat_id}")
            previous_end = beat.t_end
        if abs(self.duration_sec - ordered[-1].t_end) > 1.0:
            raise ValueError("visual plan: duration_sec не совпадает с концом последнего бита")
        return self

    def for_d2(self) -> dict[str, Any]:
        """Только режиссёрские ориентиры для человеческой речи; без URL/служебных метаданных."""
        return {
            "format": self.format.value,
            "duration_sec": self.duration_sec,
            "opening_intent": self.opening_intent,
            "beats": [
                {
                    "exhibit_name": beat.exhibit_name,
                    "narration_intent": beat.narration_intent,
                    "what_to_show": beat.what_to_show,
                }
                for beat in self.beats
            ],
        }


class HookVariant(BaseModel):
    move: str = Field(..., min_length=1, max_length=80)
    first_frame: str = Field(..., min_length=1, max_length=300)
    first_line: str = Field(..., min_length=1, max_length=280)
    subject: str = Field(..., min_length=1, max_length=160)
    tension: str = Field(..., min_length=1, max_length=200)
    payoff: str = Field(..., min_length=1, max_length=200)
    why: str = Field(..., min_length=1, max_length=300)


class HookOptions(BaseModel):
    variants: list[HookVariant] = Field(..., min_length=5, max_length=5)


class StoryBrief(BaseModel):
    claim_id: str
    format: ReelFormat = Field(
        ReelFormat.excursion,
        description="excursion по умолчанию; argument — только если нечего показывать.",
    )
    main_thought: str = Field("", max_length=400)
    angle: str = Field(
        ...,
        min_length=1,
        max_length=280,
        description="Ход фантограммы, ломающий линейную хронологию.",
    )
    # Служебное — D2 не видит (см. for_d2).
    why_viewer: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Служебно: зачем зрителю. Не для озвучки.",
    )
    visual_evidence: str = Field(
        "",
        max_length=400,
        description="Сводка кадров; для экскурсии обычно из exhibits.",
    )
    recommended_method: str = Field(..., min_length=1)
    alternative_methods: list[str] = Field(default_factory=list, max_length=2)
    selected_structure: str = Field("none")
    selected_idea_trigger: str = Field("none")
    hook_trigger: str = Field("", max_length=80)
    opening: str = Field(
        ...,
        min_length=1,
        max_length=280,
        description="Вход: 1–2 предложения.",
    )
    audience_reason: str = Field("", max_length=300)
    share_reason: str = Field("", max_length=300)
    research_queries: list[str] = Field(default_factory=list, max_length=4)
    exhibits: list[Exhibit] = Field(
        default_factory=list,
        description="6–10 экспонатов для format=excursion.",
    )
    proof_plan: list[ProofItem] = Field(
        default_factory=list,
        description="Ровно 3 доказательства для format=argument.",
    )
    conclusion: Conclusion = Field(
        ...,
        description="Вывод из источника: цитата-опора + plain для озвучки.",
    )
    idea_pitch: str = Field("", max_length=280)
    needs_external_research: bool = False
    ending_type: EndingType
    topic_ready: bool = Field(
        True,
        description="False если в источнике нет вывода — в банк идей, не в D2.",
    )

    @model_validator(mode="after")
    def _units_match_format(self) -> StoryBrief:
        if self.format == ReelFormat.excursion:
            n = len(self.exhibits)
            if not 6 <= n <= 10:
                raise ValueError(
                    f"excursion: нужно 6–10 экспонатов, получено {n}"
                )
        elif self.format == ReelFormat.argument:
            n = len(self.proof_plan)
            if n != 3:
                raise ValueError(
                    f"argument: нужно ровно 3 proof_plan, получено {n}"
                )
        if not self.topic_ready:
            raise ValueError(
                "тема не готова: в источнике нет вывода — в банк идей"
            )
        return self

    def for_d2(self) -> dict[str, Any]:
        """Только озвучиваемый слой. Служебные поля сюда не попадают."""
        payload: dict[str, Any] = {
            "claim_id": self.claim_id,
            "format": self.format.value,
            "main_thought": self.main_thought,
            "angle": self.angle,
            "opening": self.opening,
            "conclusion": {
                "plain": self.conclusion.plain,
                # source_quote — опора для модели «не расширяй»; в речь не тащить.
                "do_not_voice_quote": self.conclusion.source_quote,
            },
        }
        if self.format == ReelFormat.excursion:
            payload["exhibits"] = [
                {
                    "name": e.name,
                    "what_to_see": e.what_to_see,
                    **({"note": e.note} if e.note else {}),
                }
                for e in self.exhibits
            ]
        else:
            payload["proof_plan"] = [
                item.model_dump(mode="json") for item in self.proof_plan
            ]
        return payload

    def source_anchors(self) -> list[str]:
        """Цитаты для окон источника / E-check."""
        anchors: list[str] = [self.conclusion.source_quote]
        if self.format == ReelFormat.argument:
            anchors.extend(p.source_quote for p in self.proof_plan)
        else:
            anchors.extend(
                e.source_quote for e in self.exhibits if e.source_quote
            )
        if self.visual_evidence:
            anchors.append(self.visual_evidence)
        return [a for a in anchors if a]


class MonologueDraft(BaseModel):
    claim_id: str
    text: str = Field(..., min_length=1)
    word_count: int = Field(..., ge=1)
    story_method: str
    ending_type: EndingType
    format: ReelFormat = ReelFormat.excursion


class ResearchFact(BaseModel):
    fact: str = Field(..., min_length=1, max_length=500)
    source_url: str = Field(..., min_length=1)
    source_title: str = ""
    why_it_matters: str = Field(..., min_length=1, max_length=300)


class ResearchPack(BaseModel):
    claim_id: str
    facts: list[ResearchFact] = Field(default_factory=list, max_length=8)
    gaps: list[str] = Field(default_factory=list)
    summary: str = Field(..., min_length=1, max_length=800)


class FactIssue(BaseModel):
    quote: str = Field(..., min_length=1)
    issue: str = Field(..., min_length=1)
    severity: int = Field(..., ge=1, le=5)


class MonologueCheck(BaseModel):
    claim_id: str
    factual_issues: list[FactIssue] = Field(default_factory=list)
    overclaim_issues: list[FactIssue] = Field(default_factory=list)
    passes: bool
    summary: str = Field(..., min_length=1, max_length=500)


# Совместимость импортов
FormatLiteral = Literal["excursion", "argument"]
