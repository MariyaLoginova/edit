from __future__ import annotations

import json

from edit.graph import build_material_graph, build_v2_slice_graph
from models import ClaimCard
from tests.claim_factory import abundant_searcher, make_claim
from tests.fakes import FakeLLM
from tests.test_a2_claim_miner import _good_card


def _claim() -> ClaimCard:
    return make_claim()


def _is_a2(sys_msg: str) -> bool:
    return "ClaimCard" in sys_msg or "визуальной культуре" in sys_msg or "короткие ролики" in sys_msg


def _is_c1(sys_msg: str) -> bool:
    return "собираешь материал" in sys_msg or "support_flags" in sys_msg


def _is_c3(sys_msg: str) -> bool:
    return "мягкий фактчекер" in sys_msg or "ВЫДУМАННЫХ" in sys_msg or "invented_items" in sys_msg


def test_material_graph_freezes_on_ok():
    searcher = abundant_searcher()

    def llm_router(messages):
        sys_msg = messages[0]["content"]
        if _is_c3(sys_msg):
            return json.dumps({"ok": True, "invented_items": [], "rationale": "ok"})
        return json.dumps(
            {"material_notes": "подтверждение ухода", "support_flags": [True]}
        )

    graph = build_material_graph(llm=FakeLLM(llm_router), searcher=searcher)
    out = graph.invoke({"claims": [_claim()], "selected_claim_id": _claim().claim_id})
    assert out["dossier"].frozen is True


def test_v2_slice_blocks_on_e1_fail(fashion_source, script_weak):
    """Слабый сценарий с чужим claim_id → E1 блокирует до E-критика."""
    segment = fashion_source.segments[0]
    card = _good_card(segment)
    searcher = abundant_searcher()
    step = {"n": 0}

    def llm_router(messages):
        # 1) A2 2) C1 3) C3 — E-критик не должен вызваться
        step["n"] += 1
        sys_msg = messages[0]["content"]
        if step["n"] == 1 or _is_a2(sys_msg):
            return json.dumps([card], ensure_ascii=False)
        if _is_c1(sys_msg):
            return json.dumps(
                {"material_notes": "подтверждение ухода", "support_flags": [True]},
                ensure_ascii=False,
            )
        return json.dumps({"ok": True, "invented_items": [], "rationale": "ok"})

    llm = FakeLLM(llm_router)
    graph = build_v2_slice_graph(llm=llm, searcher=searcher)
    out = graph.invoke(
        {
            "source_map": fashion_source,
            "selected_claim_id": card["claim_id"],
            "script": script_weak,  # содержит heraldic-blue-aside
        }
    )
    assert out["dossier"].frozen is True
    assert out["trace"] is not None
    assert out["trace"].passes is False
    assert out["blocked_for_production"] is True
    assert out.get("critique") is None
    assert out.get("retention") is None


def test_v2_slice_reaches_e2_when_traced(fashion_source, script_strong):
    segment = fashion_source.segments[0]
    card = _good_card(segment)
    # script_strong already uses lbd-maintenance-not-luxury
    assert script_strong.claim_id == card["claim_id"]

    searcher = abundant_searcher()

    def llm_router(messages):
        sys_msg = messages[0]["content"]
        if _is_a2(sys_msg):
            return json.dumps([card], ensure_ascii=False)
        if _is_c1(sys_msg):
            return json.dumps(
                {"material_notes": "подтверждение ухода", "support_flags": [True]}
            )
        if _is_c3(sys_msg):
            return json.dumps({"ok": True, "invented_items": [], "rationale": "ok"})
        # E-критик
        return json.dumps(
            {
                "script_id": script_strong.script_id,
                "duration_sec": script_strong.duration_sec,
                "first3_has_hook": True,
                "open_strength": 5,
                "risks": [],
                "dropoff_score": 8,
                "attacks": [],
                "severity_max": 1,
                "retell": "Little black dress маскирует сервис, который исчез.",
                "coda_quote": script_strong.lines[-1].text,
                "coda_is_quotable": True,
                "retell_matches_coda": True,
                "passes": True,
                "summary": "ok",
            }
        )

    graph = build_v2_slice_graph(llm=FakeLLM(llm_router), searcher=searcher)
    out = graph.invoke(
        {
            "source_map": fashion_source,
            "selected_claim_id": card["claim_id"],
            "script": script_strong,
        }
    )
    assert out["trace"].passes is True
    assert out["critique"].passes is True
    assert out["retention"].passes is True
    assert out["blocked_for_production"] is False
