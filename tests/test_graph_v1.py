from __future__ import annotations

from edit.a2_claim_miner import validate_claim_payload
from edit.graph import build_a2_only_graph, build_e2_only_graph, build_vertical_slice_graph
from models import ClaimKind
from tests.fakes import FakeLLM
from tests.test_a2_claim_miner import _good_card
from tests.test_e2_retention_critic import _strong_report, _weak_report


def test_a2_only_graph(fashion_source):
    segment = fashion_source.segments[0]
    llm = FakeLLM([_good_card(segment)])
    graph = build_a2_only_graph(llm=llm)
    out = graph.invoke({"source_map": fashion_source})
    assert len(out["claims"]) == 1
    assert out["claims"][0].kind is ClaimKind.causal


def test_e2_only_graph_blocks_weak(script_weak):
    llm = FakeLLM(_weak_report(script_weak.script_id, script_weak.duration_sec))
    graph = build_e2_only_graph(llm=llm)
    out = graph.invoke({"script": script_weak})
    assert out["retention"].passes is False
    assert out["blocked_for_production"] is True


def test_vertical_slice_with_manual_script(fashion_source, script_strong):
    segment = fashion_source.segments[0]
    card = _good_card(segment)
    # E2 fake ignores A2 output; A2 still runs first
    calls = {"n": 0}

    def router(messages):
        calls["n"] += 1
        # first call A2, second E2
        if calls["n"] == 1:
            return __import__("json").dumps([card], ensure_ascii=False)
        return __import__("json").dumps(
            _strong_report(script_strong.script_id, script_strong.duration_sec),
            ensure_ascii=False,
        )

    llm = FakeLLM(router)
    graph = build_vertical_slice_graph(llm=llm)
    out = graph.invoke(
        {
            "source_map": fashion_source,
            "selected_claim_id": card["claim_id"],
            "script": script_strong,
        }
    )
    assert len(out["claims"]) >= 1
    assert out["retention"].passes is True
    assert out["blocked_for_production"] is False


def test_validate_helper_export():
    # smoke: helper импортируется для CLI/отладки
    assert callable(validate_claim_payload)
