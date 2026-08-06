"""Контракты личного редакционного контура (FIX-5)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EndingType(str, Enum):
    formula = "formula"
    reactive = "reactive"


class StoryBrief(BaseModel):
    claim_id: str
    recommended_method: str = Field(..., min_length=1)
    alternative_methods: list[str] = Field(default_factory=list, max_length=2)
    opening: str = Field(..., min_length=1, max_length=280)
    audience_reason: str = Field(..., min_length=1, max_length=300)
    share_reason: str = Field(..., min_length=1, max_length=300)
    ending_type: EndingType


class MonologueDraft(BaseModel):
    claim_id: str
    text: str = Field(..., min_length=1)
    word_count: int = Field(..., ge=1)
    story_method: str
    ending_type: EndingType


class FactIssue(BaseModel):
    quote: str = Field(..., min_length=1)
    issue: str = Field(..., min_length=1)
    severity: int = Field(..., ge=1, le=5)


class MonologueCheck(BaseModel):
    claim_id: str
    factual_issues: list[FactIssue] = Field(default_factory=list)
    overclaim_issues: list[FactIssue] = Field(default_factory=list)
    passes: bool
    summary: str = Field(..., max_length=500)
