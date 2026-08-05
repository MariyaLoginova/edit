"""D1 · Архитектор структуры: frozen Dossier → BeatList (с таймкодами)."""

from __future__ import annotations

from pathlib import Path

from edit.config import load_thresholds
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import BeatList, Dossier

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d1_architect.txt"


def _target_duration() -> float:
    cfg = load_thresholds().get("scenario", {})
    return float(cfg.get("target_duration_sec", 75))


def architect_beats(
    dossier: Dossier,
    *,
    llm: ChatModel | None = None,
    script_id: str | None = None,
) -> BeatList:
    if not dossier.frozen:
        raise ValueError("D1 читает только замороженное досье (после C3)")

    model = llm or get_chat_model(temperature=0.0)
    sid = script_id or f"script-{dossier.claim_id}"
    target = _target_duration()
    user = {
        "script_id": sid,
        "target_duration_sec": target,
        "dossier": {
            "claim_id": dossier.claim_id,
            "claim": dossier.claim.model_dump(mode="json"),
            "material_notes": dossier.material_notes,
            "web_confirmations": [
                c.model_dump(mode="json") for c in dossier.web_confirmations if c.supports_claim
            ],
            "visual_hint": dossier.claim.visual_hint,
        },
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    if isinstance(raw, dict):
        raw.setdefault("script_id", sid)
        raw.setdefault("claim_id", dossier.claim_id)
    beats = BeatList.model_validate(raw)
    if beats.claim_id != dossier.claim_id:
        raise ValueError("D1: claim_id BeatList не совпадает с досье")
    return beats
