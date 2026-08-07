"""E-hook: отдельный узел для короткого входа в научпоп-историю."""

from __future__ import annotations

from pathlib import Path

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
                        "proof_plan": [item.model_dump(mode="json") for item in brief.proof_plan],
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
