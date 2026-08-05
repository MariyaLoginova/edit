"""EDIT-E2 · Критик удержания: ScriptDraft → RetentionReport (диагностика, не правка)."""

from __future__ import annotations

import logging
from pathlib import Path

from edit.config import dropoff_score_threshold
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import RetentionReport, ScriptDraft

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e2_retention_critic.txt"
SEVERITY_BLOCK = 4


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def script_as_timed_text(script: ScriptDraft) -> str:
    lines = [
        f"[{line.t_start:.1f}-{line.t_end:.1f}] {line.text}" for line in script.lines
    ]
    return "\n".join(lines)


def compute_passes(
    report: RetentionReport,
    *,
    threshold: int | None = None,
) -> bool:
    """Вердикт детерминирован: порог из конфига + любой severity>=4."""
    thr = dropoff_score_threshold() if threshold is None else threshold
    if report.dropoff_score >= thr:
        return False
    if any(r.severity >= SEVERITY_BLOCK for r in report.risks):
        return False
    return True


def attach_quote_checks(report: RetentionReport, script: ScriptDraft) -> list[str]:
    """Предупреждения, если quote риска не является подстрокой сценария."""
    full = " ".join(line.text for line in script.lines)
    warnings: list[str] = []
    for i, risk in enumerate(report.risks):
        if risk.quote not in full and risk.quote not in script_as_timed_text(script):
            msg = f"risks[{i}] quote не найден в сценарии: {risk.quote!r}"
            warnings.append(msg)
            logger.warning("E2 quote check: %s", msg)
    return warnings


def finalize_report(
    report: RetentionReport,
    script: ScriptDraft,
    *,
    threshold: int | None = None,
) -> RetentionReport:
    """Нормализует id/duration и пересчитывает passes (не доверяем LLM на вердикте)."""
    passes = compute_passes(report, threshold=threshold)
    return report.model_copy(
        update={
            "script_id": script.script_id,
            "duration_sec": script.duration_sec,
            "passes": passes,
        }
    )


def critique_retention(
    script: ScriptDraft,
    *,
    llm: ChatModel | None = None,
    threshold: int | None = None,
) -> RetentionReport:
    if not script.lines:
        raise ValueError("ScriptDraft.lines пуст — E2 не на чем работать (нужны таймкоды D1)")

    thr = dropoff_score_threshold() if threshold is None else threshold
    model = llm or get_chat_model(temperature=0.0)
    user = (
        f"script_id: {script.script_id}\n"
        f"duration_sec: {script.duration_sec}\n"
        f"dropoff_score_threshold: {thr}\n"
        f"claim_id: {script.claim_id}\n\n"
        f"<script>\n{script_as_timed_text(script)}\n</script>"
    )
    response = model.invoke(
        [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user},
        ]
    )
    raw = parse_json_payload(content_text(response))
    report = RetentionReport.model_validate(raw)
    attach_quote_checks(report, script)
    return finalize_report(report, script, threshold=thr)
