"""E-критик · динамика + содержание + пересказ (FIX-4: бывш. E2+E3+E5)."""

from __future__ import annotations

from pathlib import Path
import re

from edit.config import load_thresholds
from edit.e2_retention_critic import script_as_timed_text
from edit.llm import ChatModel, get_chat_model, invoke_json
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
    last_error: Exception | None = None
    for _attempt in range(3):
        request = user
        if last_error is not None:
            request = {
                **user,
                "revision_note": f"Предыдущий JSON не прошёл схему: {last_error}",
                "output_contract": {
                    "required": [
                        "script_id",
                        "duration_sec",
                        "first3_has_hook",
                        "open_strength",
                        "risks",
                        "dropoff_score",
                        "attacks",
                        "severity_max",
                        "retell",
                        "coda_quote",
                        "coda_is_quotable",
                        "retell_matches_coda",
                        "summary",
                    ],
                    "do_not_use": ["overall_score", "verdict"],
                },
            }
        raw = invoke_json(
            model,
            [
                {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": str(request)},
            ],
            retries=2,
        )
        try:
            if not isinstance(raw, dict):
                raise ValueError("ожидался JSON-объект")
            if "script_id" not in raw and isinstance(raw.get("CritiqueReport"), dict):
                raw = raw["CritiqueReport"]
            raw.setdefault("script_id", script.script_id)
            raw.setdefault("duration_sec", script.duration_sec)
            risks = []
            for item in raw.get("risks") or []:
                if not isinstance(item, dict):
                    risks.append(item)
                    continue
                normalized = dict(item)
                if "t_start" not in normalized or "t_end" not in normalized:
                    nums = re.findall(r"\d+(?:\.\d+)?", str(normalized.get("time", "")))
                    if len(nums) >= 2:
                        normalized["t_start"], normalized["t_end"] = map(float, nums[:2])
                    else:
                        normalized["t_start"], normalized["t_end"] = 0.0, script.duration_sec
                reason = str(normalized.get("reason", ""))
                allowed_reasons = {x.value for x in DropReason}
                if reason not in allowed_reasons:
                    normalized["reason"] = str(
                        normalized.get("reason_code")
                        or normalized.get("type")
                        or "no_forward"
                    )
                    if normalized["reason"] not in allowed_reasons:
                        normalized["reason"] = "no_forward"
                normalized.setdefault(
                    "quote",
                    str(
                        normalized.get("text")
                        or normalized.get("fragment")
                        or script.lines[0].text
                    ),
                )
                normalized.setdefault("severity", 3)
                normalized.setdefault(
                    "fix_hint",
                    str(
                        normalized.get("suggestion")
                        or normalized.get("fix")
                        or item.get("reason")
                        or "Добавить новый факт, ставку или вопрос."
                    ),
                )
                normalized.setdefault("forward_question", None)
                risks.append(BeatRisk.model_validate(normalized))
            raw["risks"] = [r.model_dump(mode="json") for r in risks]
            attacks = []
            for item in raw.get("attacks") or []:
                if isinstance(item, dict):
                    normalized = dict(item)
                    if "attack" not in normalized:
                        normalized["attack"] = str(
                            normalized.get("critique")
                            or normalized.get("explanation")
                            or normalized.get("reason")
                            or normalized.get("comment")
                            or "Критик не объяснил атаку."
                        )
                    normalized.setdefault("severity", 3)
                    if normalized.get("kind") not in {
                        "banal",
                        "unsupported",
                        "non_sequitur",
                        "second_thesis",
                        "overclaim",
                        "vague",
                    }:
                        normalized["kind"] = "vague"
                    normalized.setdefault("quote", script.lines[0].text)
                    attacks.append(RedAttack.model_validate(normalized))
                else:
                    attacks.append(item)
            raw["attacks"] = [a.model_dump(mode="json") for a in attacks]
            raw.setdefault("severity_max", max((a.severity for a in attacks), default=1))
            raw.setdefault("passes", False)
            if isinstance(raw.get("summary"), str):
                raw["summary"] = raw["summary"][:500]
            return finalize_critique(CritiqueReport.model_validate(raw))
        except (ValueError, Exception) as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


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
