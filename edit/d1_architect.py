"""D1 · Архитектор: frozen Dossier → BeatList по норме канала (FIX-3)."""

from __future__ import annotations

from pathlib import Path

from edit.config import load_thresholds
from edit.llm import ChatModel, get_chat_model, invoke_json
from models import BeatList, Dossier, can_freeze

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d1_architect.txt"


def _target_duration() -> float:
    cfg = load_thresholds().get("scenario", {})
    return float(cfg.get("target_duration_sec", 45))


def _min_images() -> int:
    return int(load_thresholds().get("material", {}).get("min_images_per_state", 3))


def architect_beats(
    dossier: Dossier,
    *,
    llm: ChatModel | None = None,
    script_id: str | None = None,
) -> BeatList:
    if not dossier.frozen:
        raise ValueError("D1 читает только замороженное досье (после C3)")
    ok, problems = can_freeze(dossier, min_images_per_state=_min_images())
    if not ok:
        raise ValueError("D1: досье неполное — " + "; ".join(problems))

    model = llm or get_chat_model(temperature=0.0)
    sid = script_id or f"script-{dossier.claim_id}"
    target = _target_duration()
    claim = dossier.claim
    user = {
        "script_id": sid,
        "target_duration_sec": target,
        "mechanism_not_before_ratio": 0.55,
        "dossier": {
            "claim_id": dossier.claim_id,
            "claim": claim.claim,
            "counter_expectation": claim.counter_expectation,
            "object_anchor": claim.object_anchor,
            "visual_hint": claim.visual_hint,
            "contrast_pair": claim.contrast_pair.model_dump(mode="json"),
            "mechanism_term": claim.mechanism_term,
            "mechanism_explain": claim.mechanism_explain,
            "material_notes": dossier.material_notes,
            "web_confirmations": [
                c.model_dump(mode="json")
                for c in dossier.web_confirmations
                if c.supports_claim
            ],
        },
    }
    raw = invoke_json(
        model,
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ],
        retries=2,
    )
    if isinstance(raw, dict):
        raw.setdefault("script_id", sid)
        raw.setdefault("claim_id", dossier.claim_id)
    beats = BeatList.model_validate(raw)
    if beats.claim_id != dossier.claim_id:
        raise ValueError("D1: claim_id BeatList не совпадает с досье")
    return beats
