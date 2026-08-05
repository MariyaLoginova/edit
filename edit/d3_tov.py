"""D3 · ToV-агент: отдельный проход по словарю персонажа (без новых фактов)."""

from __future__ import annotations

from pathlib import Path

import yaml

from edit.config import ROOT
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import ScriptDraft, ToneOfVoice

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d3_tov.txt"
TOV_PATH = ROOT / "config" / "tov.yaml"


def load_tov(path: Path | None = None) -> ToneOfVoice:
    data = yaml.safe_load((path or TOV_PATH).read_text(encoding="utf-8")) or {}
    return ToneOfVoice.model_validate(data)


def apply_tov(
    script: ScriptDraft,
    *,
    llm: ChatModel | None = None,
    tov: ToneOfVoice | None = None,
) -> ScriptDraft:
    if not script.lines:
        raise ValueError("D3: пустой ScriptDraft")

    model = llm or get_chat_model(temperature=0.3)
    voice = tov or load_tov()
    user = {
        "tov": voice.model_dump(mode="json"),
        "script": script.model_dump(mode="json"),
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    if isinstance(raw, dict) and "lines" not in raw and isinstance(raw.get("script"), dict):
        raw = raw["script"]
    if isinstance(raw, dict):
        raw["script_id"] = script.script_id
        raw["claim_id"] = script.claim_id
        raw["duration_sec"] = script.duration_sec
        raw["tov_applied"] = True
        # жёстко сохраняем таймкоды и claim_id исходника
        if "lines" in raw and len(raw["lines"]) == len(script.lines):
            for i, src in enumerate(script.lines):
                raw["lines"][i]["t_start"] = src.t_start
                raw["lines"][i]["t_end"] = src.t_end
                raw["lines"][i]["claim_id"] = src.claim_id
                raw["lines"][i]["beat_id"] = src.beat_id
    out = ScriptDraft.model_validate(raw)
    if len(out.lines) != len(script.lines):
        raise ValueError("D3: нельзя менять число строк — только wording")
    return out
