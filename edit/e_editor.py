"""E-редактор до сценария: форма, хук и причина переслать (FIX-5)."""

from __future__ import annotations

from pathlib import Path

import yaml

from edit.audience import load_audience
from edit.config import ROOT
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import ClaimCard, EndingType, StoryBrief

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e_editor.txt"
METHODS_PATH = ROOT / "config" / "story_methods.yaml"
HOOKS_PATH = ROOT / "config" / "hook_triggers.yaml"


def load_story_methods() -> list[dict]:
    return yaml.safe_load(METHODS_PATH.read_text(encoding="utf-8")) or []


def load_hook_triggers() -> list[dict]:
    return yaml.safe_load(HOOKS_PATH.read_text(encoding="utf-8")) or []


def plan_story(claim: ClaimCard, *, llm: ChatModel | None = None) -> StoryBrief:
    model = llm or get_chat_model(temperature=0.2)
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {
                "role": "user",
                "content": str(
                    {
                        "claim": claim.model_dump(mode="json"),
                        "audience": load_audience(),
                        "menu_story_methods": load_story_methods(),
                        "hook_triggers": load_hook_triggers(),
                    }
                ),
            },
        ]
    )
    raw = parse_json_payload(content_text(response))
    if not isinstance(raw, dict):
        raise ValueError("E-редактор: ожидался JSON-объект")
    raw.setdefault("claim_id", claim.claim_id)
    raw.setdefault("ending_type", EndingType.formula.value)
    return StoryBrief.model_validate(raw)
