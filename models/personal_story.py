"""Контракты личного редакционного контура (FIX-5)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EndingType(str, Enum):
    formula = "formula"
    reactive = "reactive"


class ProofItem(BaseModel):
    point: str = Field(..., min_length=1, max_length=300)
    source_quote: str = Field(
        ...,
        min_length=1,
        max_length=700,
        description="Дословная непрерывная цитата из первичного текста.",
    )


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
    main_thought: str = Field("", max_length=400)
    visual_evidence: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description=(
            "Что зритель увидит на экране в доказательство тезиса: "
            "конкретные кадры/предметы, не рассуждение."
        ),
    )
    recommended_method: str = Field(..., min_length=1)
    alternative_methods: list[str] = Field(default_factory=list, max_length=2)
    selected_structure: str = Field(
        "none",
        description=(
            "id структуры из config/reel_structures.yaml или none, "
            "если библиотека не подходит."
        ),
    )
    hook_trigger: str = Field("", max_length=80)
    opening: str = Field(
        ...,
        min_length=1,
        max_length=280,
        description="Черновик хука: 1–2 ярких предложения для озвучки.",
    )
    audience_reason: str = Field(..., min_length=1, max_length=300)
    share_reason: str = Field(..., min_length=1, max_length=300)
    research_queries: list[str] = Field(default_factory=list, max_length=4)
    proof_plan: list[ProofItem] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Ровно три доказательства с дословной опорой в первичном тексте.",
    )
    idea_pitch: str = Field(
        "",
        max_length=280,
        description="Личный питч «Я бы…» / «А если…?» — куда образ ляжет сейчас.",
    )
    needs_external_research: bool = Field(
        False,
        description="True только если линии нужны внешняя дата, цифра или независимое подтверждение.",
    )
    ending_type: EndingType


class MonologueDraft(BaseModel):
    claim_id: str
    text: str = Field(..., min_length=1)
    word_count: int = Field(..., ge=1)
    story_method: str
    ending_type: EndingType


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
