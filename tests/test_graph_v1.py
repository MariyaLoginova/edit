from __future__ import annotations

import json

from edit.a2_claim_miner import validate_claim_payload
from edit.graph import build_a2_only_graph, build_e2_only_graph, build_vertical_slice_graph
from models import ClaimKind
from tests.claim_factory import make_frozen_dossier
from tests.fakes import FakeLLM
from tests.test_a2_claim_miner import _good_card
from tests.test_e2_retention_critic import _strong_report, _weak_report


def _as_critique(base: dict, script, *, pass_retell: bool) -> dict:
    """RetentionReport-словарь → CritiqueReport для E-критика."""
    return {
        **base,
        "attacks": [],
        "severity_max": 1,
        "retell": "Little black dress маскирует сервис ухода.",
        "coda_quote": script.lines[-1].text,
        "coda_is_quotable": pass_retell,
        "retell_matches_coda": pass_retell,
    }


def test_a2_only_graph(fashion_source):
    segment = fashion_source.segments[0]
    card = _good_card(segment)
    axes = {
        "topic_id": card["claim_id"],
        "showable": {"value": 3, "why": "Есть архивные кадры платья."},
        "surprise": {"value": 4, "why": "Сервис важнее статуса."},
        "recognizable": {"value": 5, "why": "LBD узнаваем."},
        "social_currency": {"value": 4, "why": "Хочется переслать коллеге."},
        "arguable": {"value": 3, "why": "Спор статус vs сервис."},
        "supersystem": {"value": 4, "why": "Уход как скрытый драйвер моды."},
    }
    llm = FakeLLM(queue=[[card], [axes]])
    graph = build_a2_only_graph(llm=llm)
    out = graph.invoke({"source_map": fashion_source})
    assert len(out["claims"]) == 1
    assert out["claims"][0].kind is ClaimKind.causal
    assert out["topic_candidates"][0].topic_id == card["claim_id"]
    assert out["scored_topics"][0].verdict == "produce"
    assert out["scored_topics"][0].total > 3


def test_e2_only_graph_blocks_weak(script_weak):
    dossier = make_frozen_dossier()
    payload = _as_critique(
        _weak_report(script_weak.script_id, script_weak.duration_sec),
        script_weak,
        pass_retell=False,
    )
    llm = FakeLLM(payload)
    graph = build_e2_only_graph(llm=llm)
    out = graph.invoke({"script": script_weak, "dossier": dossier})
    assert out["critique"].passes is False
    assert out["retention"].passes is False
    assert out["blocked_for_production"] is True


def test_vertical_slice_with_manual_script(fashion_source, script_strong):
    segment = fashion_source.segments[0]
    card = _good_card(segment)
    dossier = make_frozen_dossier()
    calls = {"n": 0}

    def router(messages):
        calls["n"] += 1
        sys_msg = messages[0]["content"]
        if "ClaimCard" in sys_msg or "визуальной культуре" in sys_msg or calls["n"] == 1:
            return json.dumps([card], ensure_ascii=False)
        return json.dumps(
            _as_critique(
                _strong_report(script_strong.script_id, script_strong.duration_sec),
                script_strong,
                pass_retell=True,
            ),
            ensure_ascii=False,
        )

    llm = FakeLLM(router)
    graph = build_vertical_slice_graph(llm=llm)
    out = graph.invoke(
        {
            "source_map": fashion_source,
            "selected_claim_id": card["claim_id"],
            "script": script_strong,
            "dossier": dossier,
        }
    )
    assert len(out["claims"]) >= 1
    assert out["critique"].passes is True
    assert out["retention"].passes is True
    assert out["blocked_for_production"] is False


def test_validate_helper_export():
    # smoke: helper импортируется для CLI/отладки
    assert callable(validate_claim_payload)
