"""EDIT-E2 · Критик удержания: ScriptDraft → RetentionReport (диагностика, не правка)."""

from __future__ import annotations

import logging
from pathlib import Path

from edit.config import dropoff_score_threshold
from edit.llm import ChatModel, get_chat_model, invoke_json
from models import RetentionReport, ScriptDraft

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e2_retention_critic.txt"
SEVERITY_BLOCK = 4


def _normalize_retention_payload(raw: object) -> dict:
    """Терпимость к алиасам полей (start_sec→t_start), без «починки» смысла."""
    if not isinstance(raw, dict):
        raise TypeError(f"E2: ожидался объект RetentionReport, получено {type(raw).__name__}")
    data = dict(raw)
    risks_in = data.get("risks") or []
    risks_out: list[dict] = []
    for item in risks_in:
        if not isinstance(item, dict):
            continue
        r = dict(item)
        if "t_start" not in r and "start_sec" in r:
            r["t_start"] = r.pop("start_sec")
        if "t_end" not in r and "end_sec" in r:
            r["t_end"] = r.pop("end_sec")
        if "reason" not in r and "drop_reason" in r:
            r["reason"] = r.pop("drop_reason")
        risks_out.append(r)
    data["risks"] = risks_out
    if "summary" not in data or not data["summary"]:
        data["summary"] = data.get("overview") or data.get("notes") or "См. risks."
    return data


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
        f"<script>\n{script_as_timed_text(script)}\n</script>\n\n"
        "Верни JSON RetentionReport. В каждом risk обязательны поля: "
        "t_start, t_end, quote, reason, severity, fix_hint "
        "(и опционально forward_question). Не используй start_sec/end_sec."
    )
    raw = invoke_json(
        model,
        [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user},
        ],
        retries=2,
    )
    report = RetentionReport.model_validate(_normalize_retention_payload(raw))
    attach_quote_checks(report, script)
    return finalize_report(report, script, threshold=thr)
