from __future__ import annotations

import json

from edit.graph import build_personal_story_graph
from edit.search import SearchHit
from tests.claim_factory import make_claim
from tests.fakes import FakeLLM, FakeSearcher


def test_personal_story_graph_uses_three_llm_calls():
    claim = make_claim()
    monologue = " ".join(["я"] * 100)

    def router(messages):
        system = messages[0]["content"]
        if "редактор личного канала" in system:
            return json.dumps({
                "claim_id": claim.claim_id,
                "recommended_method": "a_vot_nifiga",
                "alternative_methods": ["bylo_stalo"],
                "opening": "Неожиданный факт.",
                "audience_reason": "Не банально.",
                "share_reason": "Есть чем поделиться.",
                "ending_type": "formula",
            })
        if "Рассказываешь от первого лица" in system:
            return monologue
        if "фактчекер личного ролика" in system:
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
        {"claims": [claim], "selected_claim_id": claim.claim_id}
    )
    assert out["monologue"].word_count == 100
    assert out["monologue_check"].passes is True
    assert len(llm.calls) == 3
