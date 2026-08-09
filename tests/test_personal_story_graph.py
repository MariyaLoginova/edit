from __future__ import annotations

import json

from edit.graph import build_personal_story_graph
from edit.search import SearchHit
from tests.claim_factory import make_claim
from tests.fakes import FakeLLM, FakeSearcher


def test_personal_story_graph_uses_three_llm_calls():
    claim = make_claim()
    monologue = " ".join(["я"] * 450)

    def router(messages):
        system = messages[0]["content"]
        if "редактор канала" in system or "редактор личного канала" in system:
            return json.dumps({
                "claim_id": claim.claim_id,
                "format": "argument",
                "main_thought": "Платье работает как инфраструктура городского дня.",
                "angle": "увеличить до предела — платье как городская инженерия",
                "why_viewer": "Служебно: нейтральное платье как инженерия дня.",
                "visual_evidence": "чёрное прямое платье и городская коммютерша",
                "recommended_method": "a_vot_nifiga",
                "alternative_methods": ["bylo_stalo"],
                "opening": "Неожиданный факт.",
                "audience_reason": "Служебно.",
                "share_reason": "Есть чем поделиться.",
                "proof_plan": [
                    {"point": "деталь 1", "source_quote": "visual evidence one"},
                    {"point": "деталь 2", "source_quote": "visual evidence two"},
                    {"point": "деталь 3", "source_quote": "visual evidence three"},
                ],
                "conclusion": {
                    "source_quote": "visual evidence one",
                    "plain": "Платье держит день целиком.",
                },
                "needs_external_research": False,
                "selected_structure": "myth_bust",
                "selected_idea_trigger": "myth_series",
                "ending_type": "formula",
                "topic_ready": True,
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
        if "визуальный исследователь" in system:
            return json.dumps({
                "claim_id": claim.claim_id,
                "queries": [
                    {"query": f"archive {i}", "purpose": "найти первичный визуал"}
                    for i in range(4)
                ],
            })
        if "режиссёр-исследователь" in system:
            return json.dumps({
                "claim_id": claim.claim_id,
                "format": "argument",
                "duration_sec": 240,
                "opening_intent": "Крупно показать платье.",
                "beats": [
                    {
                        "beat_id": f"b{i}",
                        "t_start": start,
                        "t_end": end,
                        "exhibit_name": name,
                        "narration_intent": "Коротко показать улику.",
                        "context_fact": "Контекст этой улики.",
                        "what_to_show": "Архивный кадр и крупная деталь.",
                        "source_quote": "visual evidence one",
                        "source_url": None,
                        "image_query": "black dress Chanel archive",
                    }
                    for i, (start, end, name) in enumerate(
                        (
                            (0, 45, "Вход"),
                            (45, 100, "Первая улика"),
                            (100, 165, "Вторая улика"),
                            (165, 240, "Вывод"),
                        ),
                        start=1,
                    )
                ],
            })
        if (
            "рассматриваешь" in system.lower()
            or "Говоришь со зрителем" in system
            or "от первого лица" in system
        ):
            return monologue + " Какое страннее?"
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
        if "фактчекер" in system:
            return json.dumps({
                "claim_id": claim.claim_id,
                "factual_issues": [],
                "overclaim_issues": [],
                "passes": True,
                "summary": "Факты и перебор в норме.",
            })
        raise AssertionError(system[:200])

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
    assert 420 <= out["monologue"].word_count <= 700
    assert out["monologue_check"].passes is True
    assert len(out["hook_options"].variants) == 5
    assert out["visual_scenario_plan"].duration_sec == 240
    assert out["visual_research_pack"].search_status == "ok"
    assert len(llm.calls) == 6
