"""E5 · Тест пересказа одним предложением → кода."""

from __future__ import annotations

from pathlib import Path

from edit.e2_retention_critic import script_as_timed_text
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import RetellReport, ScriptDraft

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e5_retell.txt"


def _coda_text(script: ScriptDraft, *, last_n: int = 2) -> str:
    if not script.lines:
        return ""
    return " ".join(line.text for line in script.lines[-last_n:])


def finalize_retell(report: RetellReport) -> RetellReport:
    passes = bool(report.coda_is_quotable and report.retell_matches_coda)
    return report.model_copy(update={"passes": passes})


def evaluate_retell(
    script: ScriptDraft,
    *,
    llm: ChatModel | None = None,
) -> RetellReport:
    model = llm or get_chat_model(temperature=0.0)
    user = {
        "script_id": script.script_id,
        "script_timed": script_as_timed_text(script),
        "coda_hint": _coda_text(script),
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    if isinstance(raw, dict):
        raw.setdefault("script_id", script.script_id)
        raw.setdefault("coda_quote", _coda_text(script))
    report = RetellReport.model_validate(raw)
    return finalize_retell(report)
