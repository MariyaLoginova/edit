"""E3 · Красный критик: враждебный разнос по СОДЕРЖАНИЮ (не динамике)."""

from __future__ import annotations

from pathlib import Path

from edit.e2_retention_critic import script_as_timed_text
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import Dossier, RedCritique, ScriptDraft

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e3_red_critic.txt"
SEVERITY_BLOCK = 4


def finalize_red(report: RedCritique) -> RedCritique:
    severity_max = max((a.severity for a in report.attacks), default=1)
    passes = not any(a.severity >= SEVERITY_BLOCK for a in report.attacks)
    return report.model_copy(update={"severity_max": severity_max, "passes": passes})


def critique_content(
    script: ScriptDraft,
    dossier: Dossier,
    *,
    llm: ChatModel | None = None,
) -> RedCritique:
    if not dossier.frozen:
        raise ValueError("E3: досье должно быть заморожено")
    model = llm or get_chat_model(temperature=0.0)
    user = {
        "script_id": script.script_id,
        "dossier_claim": dossier.claim.model_dump(mode="json"),
        "material_notes": dossier.material_notes,
        "script": script_as_timed_text(script),
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
    report = RedCritique.model_validate(raw)
    return finalize_red(report)
