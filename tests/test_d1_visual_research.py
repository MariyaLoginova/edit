from __future__ import annotations

from edit.d1_visual_research import research_visual_material
from edit.search import SearchHit
from tests.brief_factory import make_excursion_brief
from tests.claim_factory import make_frozen_dossier
from tests.fakes import FakeLLM, FakeSearcher


def test_visual_research_runs_web_and_image_search_for_each_query():
    dossier = make_frozen_dossier()
    brief = make_excursion_brief()
    llm = FakeLLM(
        {
            "claim_id": dossier.claim_id,
            "queries": [
                {"query": f"archive query {i}", "purpose": "найти историю оригинала"}
                for i in range(4)
            ],
        }
    )
    searcher = FakeSearcher(
        web=[SearchHit(url="https://archive.example/page", title="archive", snippet="source")],
        images=[SearchHit(url="https://img.example/archive.jpg", title="image", snippet="archive")],
    )
    pack = research_visual_material(dossier, brief, searcher=searcher, llm=llm)
    assert pack.search_status == "ok"
    assert len(pack.findings) == 4
    assert len(searcher.web_queries) == 4
    assert len(searcher.image_queries) == 4
    assert all(item.image_references for item in pack.findings)
