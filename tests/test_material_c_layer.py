from __future__ import annotations

import pytest

from edit.c1_material import collect_material
from edit.c2_images import collect_images
from edit.c3_soft_factcheck import soft_factcheck
from edit.search import SearchHit, soft_metadata_match
from tests.claim_factory import make_claim
from tests.fakes import FakeLLM, FakeSearcher


def _card():
    return make_claim()


def _enough_images(query_a: str, query_b: str) -> FakeSearcher:
    return FakeSearcher(
        images=[
            SearchHit(url=f"https://img.example/a{i}.jpg", title=query_a, snippet=query_a)
            for i in range(4)
        ]
        + [
            SearchHit(url=f"https://img.example/b{i}.jpg", title=query_b, snippet=query_b)
            for i in range(4)
        ]
    )


def test_soft_metadata_match():
    assert soft_metadata_match(
        "Chanel little black dress Vogue 1926",
        "Vintage Vogue cover Chanel black dress",
        "1926 fashion plate",
    )
    assert not soft_metadata_match(
        "Chanel little black dress Vogue 1926",
        "Random stock photo of mountains",
        "landscape wallpaper",
    )


def test_c1_collects_web_confirmations():
    searcher = FakeSearcher(
        web=[
            SearchHit(
                url="https://example.com/lbd",
                title="Little black dress history",
                snippet="required almost no maintenance",
            )
        ]
    )
    llm = FakeLLM(
        {
            "material_notes": "Сниппет подтверждает тезис про низкий уход.",
            "support_flags": [True],
        }
    )
    dossier = collect_material(_card(), searcher=searcher, llm=llm)
    assert dossier.frozen is False
    assert len(dossier.web_confirmations) == 1
    assert "низкий уход" in dossier.material_notes


def test_c2_packs_images_by_ab_states():
    card = _card()
    searcher = _enough_images(card.contrast_pair.state_a, card.contrast_pair.state_b)
    dossier = collect_material(card, searcher=searcher, llm=None)
    dossier = collect_images(dossier, searcher=searcher)
    assert dossier.image_candidates.search_status == "ok"
    assert len(dossier.image_candidates.for_state_a) >= 1
    assert len(dossier.image_candidates.for_state_b) >= 1
    assert len(searcher.image_queries) == 2


def test_c3_ok_freezes_full_dossier():
    card = _card()
    searcher = FakeSearcher(
        web=[SearchHit(url="https://example.com/a", title="t", snippet="maintenance")]
    )
    dossier = collect_material(
        card,
        searcher=searcher,
        llm=FakeLLM(
            {
                "material_notes": "Подтверждение maintenance для LBD.",
                "support_flags": [True],
            }
        ),
    )
    dossier = collect_images(
        dossier,
        searcher=_enough_images(card.contrast_pair.state_a, card.contrast_pair.state_b),
    )
    dossier = soft_factcheck(
        dossier,
        llm=FakeLLM({"ok": True, "invented_items": [], "rationale": "нет выдумок"}),
    )
    assert dossier.frozen is True
    assert dossier.soft_factcheck and dossier.soft_factcheck.ok


def test_c3_fail_does_not_freeze():
    card = _card()
    searcher = FakeSearcher(
        web=[SearchHit(url="https://example.com/a", title="t", snippet="x")]
    )
    dossier = collect_material(
        card,
        searcher=searcher,
        llm=FakeLLM({"material_notes": "notes", "support_flags": [True]}),
    )
    dossier = collect_images(
        dossier,
        searcher=_enough_images(card.contrast_pair.state_a, card.contrast_pair.state_b),
    )
    dossier = soft_factcheck(
        dossier,
        llm=FakeLLM(
            {
                "ok": False,
                "invented_items": ["выдуманная дата 1812"],
                "rationale": "есть выдумка",
            }
        ),
    )
    assert dossier.frozen is False
    with pytest.raises(ValueError, match="soft_factcheck"):
        dossier.freeze()
