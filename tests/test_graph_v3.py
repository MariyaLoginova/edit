from __future__ import annotations

import json

from edit.graph import build_scenario_graph, build_v3_slice_graph
from models import ClaimCard, Dossier
from tests.claim_factory import abundant_searcher, make_claim, make_frozen_dossier
from tests.fakes import FakeLLM
from tests.test_a2_claim_miner import _good_card
from tests.test_d_scenario import _valid_script_payload


def _frozen_from_card(card: dict) -> Dossier:
    return make_frozen_dossier(ClaimCard.model_validate(card))


def _is_a2(sys_msg: str) -> bool:
    return "ClaimCard" in sys_msg or "визуальной культуре" in sys_msg or "короткие ролики" in sys_msg


def _is_c1(sys_msg: str) -> bool:
    return "собираешь материал" in sys_msg or "support_flags" in sys_msg


def _is_c3(sys_msg: str) -> bool:
    return "мягкий фактчекер" in sys_msg or "invented_items" in sys_msg


def _is_d2(sys_msg: str) -> bool:
    return "голос за кадром" in sys_msg


def test_scenario_graph_d2_only():
    card = make_claim().model_dump(mode="json")
    dossier = make_frozen_dossier(ClaimCard.model_validate(card))
    script_payload = _valid_script_payload(dossier.claim_id, dossier.claim)

    def router(messages):
        sys_msg = messages[0]["content"]
        assert _is_d2(sys_msg), sys_msg[:80]
        return json.dumps(script_payload)

    out = build_scenario_graph(llm=FakeLLM(router)).invoke({"dossier": dossier})
    assert out["script"].duration_sec == 45.0
    assert out["script"].tov_applied is True
    assert out["script"].lines[0].t_start == 0.0


def test_v3_slice_generates_script_then_e2(fashion_source):
    segment = fashion_source.segments[0]
    card = _good_card(segment)
    searcher = abundant_searcher()
    claim = ClaimCard.model_validate(card)
    script_payload = _valid_script_payload(card["claim_id"], claim)

    def router(messages):
        sys_msg = messages[0]["content"]
        if _is_a2(sys_msg):
            return json.dumps([card], ensure_ascii=False)
        if _is_c1(sys_msg):
            return json.dumps(
                {"material_notes": "подтверждение ухода", "support_flags": [True]}
            )
        if _is_c3(sys_msg):
            return json.dumps({"ok": True, "invented_items": [], "rationale": "ok"})
        if _is_d2(sys_msg):
            return json.dumps(script_payload)
        # E-критик
        return json.dumps(
            {
                "script_id": script_payload["script_id"],
                "duration_sec": script_payload["duration_sec"],
                "first3_has_hook": True,
                "open_strength": 5,
                "risks": [],
                "dropoff_score": 10,
                "attacks": [],
                "severity_max": 1,
                "retell": "Little black dress работает как сервис дня.",
                "coda_quote": script_payload["lines"][-1]["text"],
                "coda_is_quotable": True,
                "retell_matches_coda": True,
                "passes": True,
                "summary": "ok",
            }
        )

    out = build_v3_slice_graph(llm=FakeLLM(router), searcher=searcher).invoke(
        {
            "source_map": fashion_source,
            "selected_claim_id": card["claim_id"],
        }
    )
    assert out["dossier"].frozen is True
    assert out["script"] is not None
    assert out["script"].lines[0].t_start == 0.0
    assert out["trace"].passes is True
    assert out["critique"].passes is True
    assert out["retention"].passes is True
    assert out["blocked_for_production"] is False
