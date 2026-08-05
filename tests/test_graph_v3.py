from __future__ import annotations

import json

from edit.graph import build_scenario_graph, build_v3_slice_graph
from models import ClaimCard, Dossier
from tests.claim_factory import abundant_searcher, make_claim, make_frozen_dossier
from tests.fakes import FakeLLM
from tests.test_a2_claim_miner import _good_card
from tests.test_d_scenario import _script_from_beats, _valid_beats_payload


def _frozen_from_card(card: dict) -> Dossier:
    return make_frozen_dossier(ClaimCard.model_validate(card))


def test_scenario_graph_d1_d2_d3():
    card = make_claim().model_dump(mode="json")
    dossier = make_frozen_dossier(ClaimCard.model_validate(card))
    beats_payload = _valid_beats_payload()
    step = {"n": 0}

    def router(messages):
        step["n"] += 1
        if step["n"] == 1:
            return json.dumps(beats_payload)
        if step["n"] == 2:
            from models import BeatList

            return json.dumps(_script_from_beats(BeatList.model_validate(beats_payload)))
        # D3
        from models import BeatList

        rewritten = _script_from_beats(BeatList.model_validate(beats_payload))
        for line in rewritten["lines"]:
            line["text"] = "ToV: " + line["text"]
        return json.dumps(rewritten)

    out = build_scenario_graph(llm=FakeLLM(router)).invoke({"dossier": dossier})
    assert out["beats"].duration_sec == 45.0
    assert out["script"].tov_applied is True
    assert out["script"].lines[0].t_start == 0.0


def test_v3_slice_generates_script_then_e2(fashion_source):
    segment = fashion_source.segments[0]
    card = _good_card(segment)
    searcher = abundant_searcher()
    beats_payload = _valid_beats_payload(card["claim_id"])
    step = {"n": 0}

    def router(messages):
        step["n"] += 1
        sys_msg = messages[0]["content"]
        if "редактор-разведчик" in sys_msg:
            return json.dumps([card], ensure_ascii=False)
        if "сборщик материала" in sys_msg:
            return json.dumps(
                {"material_notes": "подтверждение ухода", "support_flags": [True]}
            )
        if "мягкий фактчекер" in sys_msg or "ВЫДУМАННЫХ" in sys_msg:
            return json.dumps({"ok": True, "invented_items": [], "rationale": "ok"})
        if "архитектор структуры" in sys_msg:
            return json.dumps(beats_payload)
        if "прозаик" in sys_msg:
            from models import BeatList

            return json.dumps(_script_from_beats(BeatList.model_validate(beats_payload)))
        if "ToV-агент" in sys_msg or "словаря персонажа" in sys_msg:
            from models import BeatList

            s = _script_from_beats(BeatList.model_validate(beats_payload))
            for line in s["lines"]:
                line["text"] = line["text"] + " ."
            return json.dumps(s)
        # E2
        return json.dumps(
            {
                "script_id": beats_payload["script_id"],
                "duration_sec": beats_payload["duration_sec"],
                "first3_has_hook": True,
                "open_strength": 5,
                "risks": [],
                "dropoff_score": 10,
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
    assert out["beats"] is not None
    assert out["script"] is not None
    assert out["script"].lines[0].t_start == 0.0
    assert out["trace"].passes is True
    assert out["retention"].passes is True
    assert out["blocked_for_production"] is False
