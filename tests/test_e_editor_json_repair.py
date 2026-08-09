from __future__ import annotations

import json

from edit.e_editor import plan_story
from tests.claim_factory import make_claim
from tests.fakes import FakeLLM


def test_e_editor_retries_once_after_malformed_json():
    claim = make_claim()
    source = "цитата вывода; a; b; c; d; e; f"
    valid = {
        "claim_id": claim.claim_id,
        "format": "excursion",
        "main_thought": "Коллекция показывает смену силуэтов.",
        "angle": "уменьшить до минимума — смотреть на один силуэт",
        "why_viewer": "Служебно: зрителю знакомы эти силуэты.",
        "recommended_method": "odna_detal",
        "opening": "Соберём их в ряд.",
        "exhibits": [
            {"name": name, "what_to_see": "деталь в кадре"}
            for name in ("a", "b", "c", "d", "e", "f")
        ],
        "conclusion": {"source_quote": "цитата вывода", "plain": "Вывод автора."},
        "idea_pitch": "",
        "ending_type": "reactive",
    }
    calls = 0

    def router(messages):
        nonlocal calls
        calls += 1
        return '{"format": "excursion", broken' if calls == 1 else json.dumps(valid)

    brief = plan_story(claim, primary_text=source, llm=FakeLLM(router))
    assert brief.format.value == "excursion"
    assert calls == 2
