"""E-hook: отдельный узел для короткого входа в научпоп-историю."""

from __future__ import annotations

from pathlib import Path

from edit.library import load_hook_formulas, load_open_second_triggers
from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_personal_story_model
from models import HookOptions, StoryBrief

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e_hook.txt"


def write_hook(brief: StoryBrief, *, llm: ChatModel | None = None) -> HookOptions:
    model = llm or get_personal_story_model(temperature=0.3)
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {
                "role": "user",
                "content": str(
                    {
                        "main_thought": brief.main_thought,
                        "visual_evidence": brief.visual_evidence,
                        "proof_plan": [
                            item.model_dump(mode="json") for item in brief.proof_plan
                        ],
                        "selected_structure": brief.selected_structure,
                        "selected_idea_trigger": brief.selected_idea_trigger,
                        "menu_hook_formulas": load_hook_formulas(),
                        "menu_open_second_triggers": load_open_second_triggers(),
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
