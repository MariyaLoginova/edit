"""E-hook: короткий вход. Служебные поля брифа не тащим в озвучку дальше."""

from __future__ import annotations

from pathlib import Path

from edit.library import (
    compose_system_prompt,
    load_hook_formulas,
    load_open_second_triggers,
)
from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_personal_story_model
from models import HookOptions, ReelFormat, StoryBrief

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e_hook.txt"


def write_hook(brief: StoryBrief, *, llm: ChatModel | None = None) -> HookOptions:
    model = llm or get_personal_story_model(temperature=0.3)
    units = (
        {"exhibits": [e.model_dump(mode="json") for e in brief.exhibits]}
        if brief.format in {ReelFormat.excursion, ReelFormat.narrative}
        else {
            "proof_plan": [
                item.model_dump(mode="json") for item in brief.proof_plan
            ]
        }
    )
    response = model.invoke(
        [
            {
                "role": "system",
                "content": compose_system_prompt(PROMPT_PATH, "e_hook_menu"),
            },
            {
                "role": "user",
                "content": str(
                    {
                        "format": brief.format.value,
                        "main_thought": brief.main_thought,
                        "angle": brief.angle,
                        "opening": brief.opening,
                        "visual_evidence": brief.visual_evidence,
                        **units,
                        "selected_structure": brief.selected_structure,
                        "selected_idea_trigger": brief.selected_idea_trigger,
                        "menu_hook_formulas": load_hook_formulas(),
                        "menu_open_second_triggers": load_open_second_triggers(),
                        # why_viewer намеренно не передаём — иначе хук озвучит аудиторию.
                    }
                ),
            },
        ]
    )
    raw = parse_json_payload(content_text(response))
    if isinstance(raw, list):
        raw = {"variants": raw}
    if not isinstance(raw, dict):
        raise ValueError("E-hook: ожидался JSON-массив из пяти вариантов")
    return HookOptions.model_validate(raw)
