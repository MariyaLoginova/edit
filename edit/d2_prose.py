"""D2 · Прозаик: пишет ТОЛЬКО из досье по BeatList → ScriptDraft."""

from __future__ import annotations

from pathlib import Path

from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import BeatList, Dossier, ScriptDraft

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d2_prose.txt"


def write_prose(
    dossier: Dossier,
    beats: BeatList,
    *,
    llm: ChatModel | None = None,
) -> ScriptDraft:
    if not dossier.frozen:
        raise ValueError("D2 пишет только из замороженного досье")
    if beats.claim_id != dossier.claim_id:
        raise ValueError("D2: BeatList.claim_id != dossier.claim_id")

    model = llm or get_chat_model(temperature=0.2)
    user = {
        "dossier": {
            "claim_id": dossier.claim_id,
            "claim": dossier.claim.claim,
            "counter_expectation": dossier.claim.counter_expectation,
            "visual_hint": dossier.claim.visual_hint,
            "citation": dossier.claim.citation.model_dump(mode="json"),
            "scope": dossier.claim.scope.model_dump(mode="json"),
            "material_notes": dossier.material_notes,
            "web_confirmations": [
                {"title": c.title, "snippet": c.snippet}
                for c in dossier.web_confirmations
                if c.supports_claim
            ],
        },
        "beats": beats.model_dump(mode="json"),
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    if isinstance(raw, dict):
        raw.setdefault("script_id", beats.script_id)
        raw.setdefault("claim_id", dossier.claim_id)
        raw["tov_applied"] = False
    script = ScriptDraft.model_validate(raw)
    _assert_grounded(script, dossier, beats)
    return script


def _assert_grounded(script: ScriptDraft, dossier: Dossier, beats: BeatList) -> None:
    if script.claim_id != dossier.claim_id:
        raise ValueError("D2: script.claim_id не из досье")
    if abs(script.duration_sec - beats.duration_sec) > 1.0:
        raise ValueError("D2: duration_sec сценария заметно разошёлся с BeatList")
    for line in script.lines:
        if line.claim_id is None:
            continue
        if line.claim_id != dossier.claim_id:
            raise ValueError(
                f"D2: line с чужим claim_id={line.claim_id!r} — факт вне досье"
            )
