"""E1 · Аудитор трассируемости: каждый факт → claim_id."""

from enum import Enum

from pydantic import BaseModel, Field


class TraceReason(str, Enum):
    missing_claim_id = "missing_claim_id"
    unknown_claim_id = "unknown_claim_id"
    dossier_not_frozen = "dossier_not_frozen"
    claim_mismatch = "claim_mismatch"


class TraceIssue(BaseModel):
    line_index: int = Field(..., ge=0)
    text: str
    reason: TraceReason
    detail: str = ""


class TraceReport(BaseModel):
    script_id: str
    dossier_claim_id: str
    passes: bool
    issues: list[TraceIssue]
    summary: str = Field(..., max_length=400)
