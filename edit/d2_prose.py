"""D2 · Прозаик: пишет ТОЛЬКО из досье по BeatList → ScriptDraft (FIX-3)."""

from __future__ import annotations

from pathlib import Path

from edit.config import load_thresholds
from edit.llm import ChatModel, get_chat_model, invoke_json
from models import BeatList, Dossier, ScriptDraft, can_freeze

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d2_prose.txt"

DEFAULT_STOP = [
    "странно, но",
    "формула простая",
    "заметь",
    "через миг",
    "на самом деле всё просто",
    "а теперь представь",
]


def _stop_phrases() -> list[str]:
    cfg = load_thresholds().get("scenario", {}).get("meta_stop_phrases") or []
    return list(dict.fromkeys([*DEFAULT_STOP, *[str(x) for x in cfg]]))


def _min_images() -> int:
    return int(load_thresholds().get("material", {}).get("min_images_per_state", 3))


def write_prose(
    dossier: Dossier,
    beats: BeatList,
    *,
    llm: ChatModel | None = None,
) -> ScriptDraft:
    if not dossier.frozen:
        raise ValueError("D2 пишет только из замороженного досье")
    ok, problems = can_freeze(dossier, min_images_per_state=_min_images())
    if not ok:
        raise ValueError(
            "D2: досье неполное (обход freeze?) — " + "; ".join(problems)
        )
    if beats.claim_id != dossier.claim_id:
        raise ValueError("D2: BeatList.claim_id != dossier.claim_id")

    claim = dossier.claim
    stop = _stop_phrases()
    model = llm or get_chat_model(temperature=0.2)
    user = {
        "dossier": {
            "claim_id": dossier.claim_id,
            "claim": claim.claim,
            "counter_expectation": claim.counter_expectation,
            "visual_hint": claim.visual_hint,
            "object_anchor": claim.object_anchor,
            "contrast_pair": claim.contrast_pair.model_dump(mode="json"),
            "mechanism_term": claim.mechanism_term,
            "mechanism_explain": claim.mechanism_explain,
            "citation": claim.citation.model_dump(mode="json"),
            "scope": claim.scope.model_dump(mode="json"),
            "material_notes": dossier.material_notes,
            "web_confirmations": [
                {"title": c.title, "snippet": c.snippet}
                for c in dossier.web_confirmations
                if c.supports_claim
            ],
        },
        "beats": beats.model_dump(mode="json"),
        "meta_stop_phrases": stop,
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
        raw.setdefault("script_id", beats.script_id)
        raw.setdefault("claim_id", dossier.claim_id)
        raw["tov_applied"] = False
    script = ScriptDraft.model_validate(raw)
    _assert_grounded(script, dossier, beats)
    _assert_no_stop_phrases(script, stop)
    _assert_object_grounding(script, dossier)
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


def _assert_no_stop_phrases(script: ScriptDraft, stop: list[str]) -> None:
    joined = " ".join(line.text.lower() for line in script.lines)
    for phrase in stop:
        if phrase.lower() in joined:
            raise ValueError(f"D2: стоп-фраза мета-связки в озвучке: {phrase!r}")


def _assert_object_grounding(script: ScriptDraft, dossier: Dossier) -> None:
    """Каждая реплика должна цепляться к object_anchor или state_a/state_b."""
    claim = dossier.claim
    anchors = {
        *claim.object_anchor.lower().split(),
        *claim.contrast_pair.state_a.lower().split(),
        *claim.contrast_pair.state_b.lower().split(),
        *claim.visual_hint.lower().split(),
    }
    # содержательные токены ≥3
    anchors = {t.strip("«»\",.:;") for t in anchors if len(t) >= 3}
    for i, line in enumerate(script.lines):
        words = {t.strip("«»\",.:;") for t in line.text.lower().split() if len(t) >= 3}
        if not (words & anchors):
            raise ValueError(
                f"D2: line[{i}] не привязана к object_anchor/A/B: {line.text!r}"
            )
