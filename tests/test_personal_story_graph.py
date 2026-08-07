from __future__ import annotations

import json

from edit.graph import build_personal_story_graph
from edit.search import SearchHit
from tests.claim_factory import make_claim
from tests.fakes import FakeLLM, FakeSearcher


def test_personal_story_graph_uses_three_llm_calls():
    claim = make_claim()
    monologue = " ".join(["я"] * 104)

    def router(messages):
        system = messages[0]["content"]
        if "редактор личного канала" in system:
            return json.dumps({
                "claim_id": claim.claim_id,
                "main_thought": "Платье работает как инфраструктура городского дня.",
                "visual_evidence": "чёрное прямое платье и городская коммютерша",
                "recommended_method": "a_vot_nifiga",
                "alternative_methods": ["bylo_stalo"],
                "opening": "Неожиданный факт.",
                "audience_reason": "Не банально.",
                "share_reason": "Есть чем поделиться.",
                "proof_plan": [
                    {"point": "деталь 1", "source_quote": "visual evidence one"},
                    {"point": "деталь 2", "source_quote": "visual evidence two"},
                    {"point": "деталь 3", "source_quote": "visual evidence three"},
                ],
                "needs_external_research": False,
                "ending_type": "formula",
            })
        if "первые 3 секунды" in system:
            return json.dumps(
                [
                    {
                        "move": move,
                        "first_frame": "чёрное прямое платье",
                        "first_line": "Чёрное платье оказалось инфраструктурой дня.",
                        "subject": "чёрное прямое платье",
                        "tension": "оно выглядит как статус, но работает иначе",
                        "payoff": "ролик объяснит эту функцию",
                        "why": "конкретный визуальный предмет",
                    }
                    for move in ("залипание", "спрятанное", "переворот", "тихий кадр", "потеря")
                ]
            )
        if "Говоришь со зрителем вслух" in system or "Рассказываешь от первого лица" in system:
            return monologue + " Финальная формула держит историю."
        if "исследователь для личного ролика" in system:
            return json.dumps({
                "claim_id": claim.claim_id,
                "facts": [
                    {
                        "fact": "Дополнительный факт.",
                        "source_url": "https://example.com",
                        "source_title": "source",
                        "why_it_matters": "Усиливает историю.",
                    }
                ],
                "gaps": [],
                "summary": "Фактура добавлена.",
            })
        if "фактчекер" in system and "личного ролика" in system:
            return json.dumps({
                "claim_id": claim.claim_id,
                "factual_issues": [],
                "overclaim_issues": [],
                "passes": True,
                "summary": "Факты и перебор в норме.",
            })
        raise AssertionError(system)

    searcher = FakeSearcher(
        web=[SearchHit(url="https://example.com", title="source", snippet="evidence")]
    )
    llm = FakeLLM(router)
    out = build_personal_story_graph(llm=llm, searcher=searcher).invoke(
        {
            "claims": [claim],
            "selected_claim_id": claim.claim_id,
            "primary_text": (
                "visual evidence one. visual evidence two. visual evidence three. "
                "чёрное прямое платье и городская коммютерша"
            ),
        }
    )
    assert 105 <= out["monologue"].word_count <= 115
    assert out["monologue_check"].passes is True
    assert len(out["hook_options"].variants) == 5
    assert len(llm.calls) == 4
