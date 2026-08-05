"""E-критик · динамика + содержание + пересказ (FIX-4: бывш. E2+E3+E5)."""

from __future__ import annotations

from pathlib import Path

from edit.config import load_thresholds
from edit.e2_retention_critic import script_as_timed_text
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import (
    BeatRisk,
    CritiqueReport,
    Dossier,
    DropReason,
    RedAttack,
    RetentionReport,
    ScriptDraft,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e_critic.txt"


def _thresholds() -> tuple[int, int]:
    ed = load_thresholds().get("editorial", {})
    ret = load_thresholds().get("retention", {})
    drop = int(ed.get("dropoff_score_threshold", ret.get("dropoff_score_threshold", 40)))
    sev = int(ed.get("attack_severity_block", 4))
    return drop, sev


def finalize_critique(raw: CritiqueReport) -> CritiqueReport:
    drop_th, sev_block = _thresholds()
    severity_max = max((a.severity for a in raw.attacks), default=1)
    risk_block = any(getattr(r, "severity", 1) >= sev_block for r in raw.risks)
    attack_block = any(a.severity >= sev_block for a in raw.attacks)
    retell_ok = bool(raw.coda_is_quotable and raw.retell_matches_coda)
    dynamics_ok = raw.dropoff_score < drop_th and not risk_block
    content_ok = not attack_block
    passes = dynamics_ok and content_ok and retell_ok
    return raw.model_copy(
        update={"severity_max": severity_max, "passes": passes}
    )


def critique_script(
    script: ScriptDraft,
    dossier: Dossier,
    *,
    llm: ChatModel | None = None,
) -> CritiqueReport:
    if not dossier.frozen:
        raise ValueError("E-критик: досье должно быть заморожено")
    model = llm or get_chat_model(temperature=0.0)
    drop_th, sev_block = _thresholds()
    user = {
        "script_id": script.script_id,
        "duration_sec": script.duration_sec,
        "dropoff_score_threshold": drop_th,
        "attack_severity_block": sev_block,
        "dossier_claim": dossier.claim.model_dump(mode="json"),
        "material_notes": dossier.material_notes[:2000],
        "script": script_as_timed_text(script),
        "schema_hint": {
            "risks": "BeatRisk[] reason in DropReason",
            "attacks": "RedAttack[] kind in banal|unsupported|non_sequitur|second_thesis|overclaim|vague",
            "retell": "одно предложение зрителя",
            "coda_quote": "последние реплики",
        },
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    if not isinstance(raw, dict):
        raise ValueError("E-критик: ожидался JSON-объект")
    raw.setdefault("script_id", script.script_id)
    raw.setdefault("duration_sec", script.duration_sec)
    # нормализуем risks → BeatRisk
    risks_in = raw.get("risks") or []
    risks: list[BeatRisk] = []
    for item in risks_in:
        if isinstance(item, dict):
            risks.append(BeatRisk.model_validate(item))
        else:
            risks.append(item)
    raw["risks"] = [r.model_dump(mode="json") for r in risks]
    attacks_in = raw.get("attacks") or []
    attacks: list[RedAttack] = []
    for item in attacks_in:
        if isinstance(item, dict):
            attacks.append(RedAttack.model_validate(item))
        else:
            attacks.append(item)
    raw["attacks"] = [a.model_dump(mode="json") for a in attacks]
    raw.setdefault("severity_max", max((a.severity for a in attacks), default=1))
    raw.setdefault("passes", False)
    report = CritiqueReport.model_validate(raw)
    return finalize_critique(report)


def critique_as_retention(report: CritiqueReport) -> RetentionReport:
    """Адаптер для E4, который ещё ждёт RetentionReport."""
    return RetentionReport(
        script_id=report.script_id,
        duration_sec=report.duration_sec,
        first3_has_hook=report.first3_has_hook,
        open_strength=report.open_strength,
        risks=list(report.risks),
        dropoff_score=report.dropoff_score,
        passes=report.dropoff_score
        < _thresholds()[0]
        and not any(getattr(r, "severity", 1) >= 4 for r in report.risks),
        summary=report.summary[:400],
    )
