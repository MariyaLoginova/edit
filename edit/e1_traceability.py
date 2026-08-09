"""E1 · Аудитор трассируемости: каждый факт в сценарии → claim_id из досье."""

from __future__ import annotations

import re

from models import Dossier, ScriptDraft, TraceIssue, TraceReason, TraceReport

# маркеры мнения / разгона (E7) — не требуют фактовой трассировки тела
_OPINION_MARKERS = re.compile(
    r"(^\s*а если\b|^\s*(?:поэтому\s+)?я бы\b|^\s*для меня\b|а если посмотреть|спекулятивно|моя интерпретация|что если читать|"
    r"дальше\s*[—\-]\s*моя|гипотеза)",
    re.IGNORECASE,
)


def _is_opinion_or_glue(text: str) -> bool:
    t = text.strip()
    if _OPINION_MARKERS.search(t):
        return True
    # очень короткие связки без содержания
    if len(t) <= 24 and t.lower() in {
        "ну вот",
        "смотрите",
        "итак",
        "короче",
        "подписывайтесь",
    }:
        return True
    return False


def audit_traceability(script: ScriptDraft, dossier: Dossier) -> TraceReport:
    """Hard fail, если факт без claim_id или claim_id не из замороженного досье."""
    issues: list[TraceIssue] = []

    if not dossier.frozen:
        issues.append(
            TraceIssue(
                line_index=0,
                text="",
                reason=TraceReason.dossier_not_frozen,
                detail="E1 читает только замороженное досье (после C3)",
            )
        )

    if script.claim_id != dossier.claim_id:
        issues.append(
            TraceIssue(
                line_index=0,
                text=script.claim_id,
                reason=TraceReason.claim_mismatch,
                detail=(
                    f"script.claim_id={script.claim_id!r} != "
                    f"dossier.claim_id={dossier.claim_id!r}"
                ),
            )
        )

    allowed = {dossier.claim_id}

    for i, line in enumerate(script.lines):
        if line.claim_id is None:
            if _is_opinion_or_glue(line.text):
                continue
            issues.append(
                TraceIssue(
                    line_index=i,
                    text=line.text,
                    reason=TraceReason.missing_claim_id,
                    detail="фактическая реплика без claim_id",
                )
            )
            continue
        if line.claim_id not in allowed:
            issues.append(
                TraceIssue(
                    line_index=i,
                    text=line.text,
                    reason=TraceReason.unknown_claim_id,
                    detail=f"claim_id={line.claim_id!r} отсутствует в замороженном досье",
                )
            )

    passes = not issues
    if passes:
        summary = "Все фактические реплики трассируются к claim_id досье."
    else:
        summary = f"E1 fail: {len(issues)} проблем(ы) трассируемости."

    return TraceReport(
        script_id=script.script_id,
        dossier_claim_id=dossier.claim_id,
        passes=passes,
        issues=issues,
        summary=summary,
    )
