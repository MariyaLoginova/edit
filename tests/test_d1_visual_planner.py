from __future__ import annotations

from edit.d1_visual_planner import plan_visual_scenario
from models import ReelFormat
from tests.brief_factory import make_excursion_brief
from tests.claim_factory import make_frozen_dossier
from tests.fakes import FakeLLM, FakeSearcher


def test_visual_planner_collects_image_references_for_each_beat():
    dossier = make_frozen_dossier()
    brief = make_excursion_brief()
    payload = {
        "claim_id": dossier.claim_id,
        "format": "excursion",
        "duration_sec": 210,
        "opening_intent": "Разложить Барби в ряд.",
        "beats": [
            {
                "beat_id": f"b{i}",
                "t_start": (i - 1) * 35,
                "t_end": i * 35,
                "exhibit_name": exhibit.name,
                "narration_intent": "Рассмотреть деталь.",
                "context_fact": "Исторический контекст экспоната.",
                "what_to_show": exhibit.what_to_see,
                "source_quote": "source",
                "image_query": f"{exhibit.name} Barbie",
            }
            for i, exhibit in enumerate(brief.exhibits, start=1)
        ],
    }
    searcher = FakeSearcher(
        images=[
            # Универсальный референс: тестирует именно проводку поисковых запросов.
            __import__("edit.search", fromlist=["SearchHit"]).SearchHit(
                url="https://img.example/barbie.jpg", title="Barbie", snippet="archive"
            )
        ]
    )
    plan = plan_visual_scenario(
        dossier,
        brief,
        primary_text="source",
        image_searcher=searcher,
        llm=FakeLLM(payload),
    )
    assert plan.format == ReelFormat.excursion
    assert plan.duration_sec == 210
    assert plan.image_search_status == "ok"
    assert len(searcher.image_queries) == 6
    assert all(beat.image_references for beat in plan.beats)
    d2 = plan.for_d2()
    assert "image_query" not in str(d2)
    assert len(d2["beats"]) == 6
    assert d2["beats"][0]["context_fact"] == "Исторический контекст экспоната."


def test_visual_planner_keeps_plan_when_image_search_unavailable():
    dossier = make_frozen_dossier()
    brief = make_excursion_brief()
    payload = {
        "claim_id": dossier.claim_id,
        "format": "excursion",
        "duration_sec": 180,
        "opening_intent": "Разложить Барби в ряд.",
        "beats": [
            {
                "beat_id": f"b{i}",
                "t_start": (i - 1) * 30,
                "t_end": i * 30,
                "exhibit_name": exhibit.name,
                "narration_intent": "Рассмотреть деталь.",
                "context_fact": "Исторический контекст экспоната.",
                "what_to_show": exhibit.what_to_see,
                "source_quote": "material notes",
                "image_query": f"{exhibit.name} Barbie",
            }
            for i, exhibit in enumerate(brief.exhibits, start=1)
        ],
    }

    class Unavailable:
        def search_images(self, query: str, *, max_results: int = 3):
            from edit.search import SearchUnavailableError

            raise SearchUnavailableError("no Brave key")

    plan = plan_visual_scenario(
        dossier,
        brief,
        image_searcher=Unavailable(),
        llm=FakeLLM(payload),
    )
    assert plan.image_search_status == "unavailable"
    assert plan.image_search_error == "no Brave key"
