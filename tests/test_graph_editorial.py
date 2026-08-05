from __future__ import annotations

import json

from edit.graph import build_editorial_graph
from tests.fakes import FakeLLM
from tests.test_editorial_e3_e6 import _dossier, _script


def test_editorial_graph_happy_path():
    script = _script()
    # prepare compressed script once
    short = script.model_copy(
        update={
            "lines": [
                line.model_copy(update={"text": line.text[: max(1, int(len(line.text) * 0.78))]})
                for line in script.lines
            ]
        }
    )
    variants = [
        {"text": f"Крючок {i}: не роскошь, а уход", "rationale": "разрыв", "hook_strength": 5}
        for i in range(5)
    ]

    def router(messages):
        sys_msg = messages[0]["content"]
        if "критик удержания" in sys_msg:
            return json.dumps(
                {
                    "script_id": script.script_id,
                    "duration_sec": script.duration_sec,
                    "first3_has_hook": False,
                    "open_strength": 2,
                    "risks": [],
                    "dropoff_score": 5,
                    "passes": True,
                    "summary": "почти ок, opening слабый",
                }
            )
        if "КРАСНЫЙ критик" in sys_msg or "враждебная установка" in sys_msg:
            return json.dumps(
                {
                    "script_id": script.script_id,
                    "attacks": [],
                    "severity_max": 1,
                    "passes": True,
                    "summary": "содержание держится",
                }
            )
        if "генератор открытий" in sys_msg or "ПЕРВЫХ" in sys_msg:
            return json.dumps(
                {
                    "script_id": script.script_id,
                    "variants": variants,
                    "chosen_index": 0,
                    "script": script.model_dump(mode="json"),
                }
            )
        if "тест пересказа" in sys_msg or "ОДНИМ предложением" in sys_msg:
            return json.dumps(
                {
                    "script_id": script.script_id,
                    "retell": "Статус маскирует сервис ухода, который исчез.",
                    "coda_quote": script.lines[-1].text,
                    "coda_is_quotable": True,
                    "retell_matches_coda": True,
                    "passes": True,
                    "fix_hint": "",
                    "summary": "кода ок",
                }
            )
        if "компрессор" in sys_msg:
            return json.dumps(
                {
                    "script_id": script.script_id,
                    "original_chars": 1,
                    "compressed_chars": 1,
                    "reduction_ratio": 0.22,
                    "script": short.model_dump(mode="json"),
                    "passes": True,
                    "summary": "сжал",
                }
            )
        raise AssertionError(f"unexpected prompt: {sys_msg[:80]}")

    out = build_editorial_graph(llm=FakeLLM(router)).invoke(
        {"script": script, "dossier": _dossier()}
    )
    assert out["retention"].passes is True
    assert out["red_critique"].passes is True
    assert out["opening_pick"].chosen_index == 0
    assert "Крючок 0" in out["script"].lines[0].text or out["opening_pick"].chosen_text
    assert out["retell"].passes is True
    assert out["compression"].reduction_ratio > 0
    assert out["blocked_for_production"] is False


def test_editorial_gate_blocks_on_red_fail():
    script = _script()

    def router(messages):
        sys_msg = messages[0]["content"]
        if "критик удержания" in sys_msg:
            return json.dumps(
                {
                    "script_id": "s1",
                    "duration_sec": 40,
                    "first3_has_hook": True,
                    "open_strength": 5,
                    "risks": [],
                    "dropoff_score": 5,
                    "passes": True,
                    "summary": "ok",
                }
            )
        if "КРАСНЫЙ" in sys_msg or "враждебная" in sys_msg:
            return json.dumps(
                {
                    "script_id": "s1",
                    "attacks": [
                        {
                            "kind": "unsupported",
                            "quote": "Привет, сегодня про платье.",
                            "attack": "Не следует из досье.",
                            "severity": 5,
                        }
                    ],
                    "severity_max": 5,
                    "passes": False,
                    "summary": "разнос",
                }
            )
        if "открытий" in sys_msg or "ПЕРВЫХ" in sys_msg:
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
        if "пересказа" in sys_msg or "ОДНИМ" in sys_msg:
            return json.dumps(
                {
                    "script_id": "s1",
                    "retell": "ok",
                    "coda_quote": script.lines[-1].text,
                    "coda_is_quotable": True,
                    "retell_matches_coda": True,
                    "passes": True,
                    "summary": "ok",
                }
            )
        # compress
        short = script.model_copy(
            update={
                "lines": [
                    line.model_copy(update={"text": line.text[: max(1, int(len(line.text) * 0.78))]})
                    for line in script.lines
                ]
            }
        )
        return json.dumps(
            {
                "script_id": "s1",
                "original_chars": 1,
                "compressed_chars": 1,
                "reduction_ratio": 0.22,
                "script": short.model_dump(mode="json"),
                "passes": True,
                "summary": "ok",
            }
        )

    out = build_editorial_graph(llm=FakeLLM(router)).invoke(
        {"script": script, "dossier": _dossier()}
    )
    assert out["red_critique"].passes is False
    assert out["blocked_for_production"] is True
