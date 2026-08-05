from __future__ import annotations

import json

from edit.graph import build_editorial_graph
from tests.fakes import FakeLLM
from tests.test_editorial_e3_e6 import _dossier, _script


def _critique_ok(script, *, attacks=None, severity_max=1, passes_hint=True) -> dict:
    return {
        "script_id": script.script_id,
        "duration_sec": script.duration_sec,
        "first3_has_hook": False,
        "open_strength": 2,
        "risks": [],
        "dropoff_score": 5,
        "attacks": attacks or [],
        "severity_max": severity_max,
        "retell": "Статус маскирует сервис ухода, который исчез.",
        "coda_quote": script.lines[-1].text,
        "coda_is_quotable": True,
        "retell_matches_coda": True,
        "passes": passes_hint,
        "summary": "почти ок, opening слабый",
    }


def test_editorial_graph_happy_path():
    script = _script()
    variants = [
        {"text": f"Крючок {i}: не роскошь, а уход", "rationale": "разрыв", "hook_strength": 5}
        for i in range(5)
    ]

    def router(messages):
        sys_msg = messages[0]["content"]
        if "критик короткого видео" in sys_msg:
            return json.dumps(_critique_ok(script))
        if "первых ~3 секунд" in sys_msg or "OpeningPick" in sys_msg:
            return json.dumps(
                {
                    "script_id": script.script_id,
                    "variants": variants,
                    "chosen_index": 0,
                    "script": script.model_dump(mode="json"),
                }
            )
        raise AssertionError(f"unexpected prompt: {sys_msg[:80]}")

    out = build_editorial_graph(llm=FakeLLM(router)).invoke(
        {"script": script, "dossier": _dossier()}
    )
    assert out["critique"].passes is True
    assert out["retention"].passes is True
    assert out["opening_pick"].chosen_index == 0
    assert "Крючок 0" in out["script"].lines[0].text or out["opening_pick"].chosen_text
    assert out["blocked_for_production"] is False


def test_editorial_gate_blocks_on_red_fail():
    script = _script()
    attacks = [
        {
            "kind": "unsupported",
            "quote": "Привет, сегодня про платье.",
            "attack": "Не следует из досье.",
            "severity": 5,
        }
    ]

    def router(messages):
        sys_msg = messages[0]["content"]
        if "критик короткого видео" in sys_msg:
            return json.dumps(
                _critique_ok(
                    script,
                    attacks=attacks,
                    severity_max=5,
                    passes_hint=False,
                )
                | {"summary": "разнос"}
            )
        if "первых ~3 секунд" in sys_msg or "OpeningPick" in sys_msg:
            variants = [
                {"text": f"open {i}", "rationale": "r", "hook_strength": 3} for i in range(5)
            ]
            return json.dumps(
                {
                    "script_id": "s1",
                    "variants": variants,
                    "chosen_index": 0,
                    "script": script.model_dump(mode="json"),
                }
            )
        raise AssertionError(f"unexpected prompt: {sys_msg[:80]}")

    out = build_editorial_graph(llm=FakeLLM(router)).invoke(
        {"script": script, "dossier": _dossier()}
    )
    assert out["critique"].passes is False
    assert out["blocked_for_production"] is True
