from __future__ import annotations

import pytest

from edit.c1_material import collect_material
from edit.c2_images import collect_images
from edit.c3_soft_factcheck import soft_factcheck
from edit.search import SearchHit, soft_metadata_match
from models import Citation, ClaimCard, ClaimKind, Scope
from tests.fakes import FakeLLM, FakeSearcher


def _card() -> ClaimCard:
    return ClaimCard(
        claim_id="lbd-maintenance-not-luxury",
        kind=ClaimKind.causal,
        claim="Маленькое чёрное взлетело как наряд без ухода, а не как символ роскоши",
        counter_expectation="Считают, что LBD — про вневременную элегантность",
        visual_hint="Chanel little black dress Vogue 1926",
        citation=Citation(
            locator="гл. 2",
            quote="the little black dress succeeded because it required almost no maintenance",
        ),
        scope=Scope(period="1920s", region="Paris", author_or_work="Chanel"),
        source_segment_id="ch2-s1",
        confidence=0.9,
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
    assert dossier.web_confirmations[0].supports_claim is True
    assert "низкий уход" in dossier.material_notes


def test_c2_packs_images_with_soft_match_flag():
    card = _card()
    searcher = FakeSearcher(
        images=[
            SearchHit(
                url="https://img.example/lbd.jpg",
                title="Chanel little black dress 1926 Vogue",
                snippet="archive fashion plate",
            ),
            SearchHit(
                url="https://img.example/cat.jpg",
                title="Funny cat",
                snippet="pet photo",
            ),
        ]
    )
    dossier = collect_material(card, searcher=searcher, llm=None)
    dossier = collect_images(dossier, searcher=searcher)
    assert len(dossier.image_candidates) == 2
    assert dossier.image_candidates[0].soft_match is True
    assert dossier.image_candidates[0].url.endswith("lbd.jpg")


def test_c3_ok_freezes_dossier():
    searcher = FakeSearcher(
        web=[SearchHit(url="https://example.com/a", title="t", snippet="maintenance")]
    )
    dossier = collect_material(_card(), searcher=searcher, llm=None)
    dossier = collect_images(
        dossier,
        searcher=FakeSearcher(
            images=[
                SearchHit(
                    url="https://img.example/lbd.jpg",
                    title="Chanel black dress Vogue",
                    snippet="1926",
                )
            ]
        ),
    )
    llm = FakeLLM({"ok": True, "invented_items": [], "rationale": "Дат/имён-выдумок нет."})
    frozen = soft_factcheck(dossier, llm=llm, auto_freeze=True)
    assert frozen.frozen is True
    assert frozen.soft_factcheck and frozen.soft_factcheck.ok
    with pytest.raises(RuntimeError, match="заморожен"):
        frozen.ensure_mutable()


def test_c3_fail_does_not_freeze():
    dossier = collect_material(
        _card(),
        searcher=FakeSearcher(web=[SearchHit(url="https://x", title="t", snippet="s")]),
        llm=None,
    )
    llm = FakeLLM(
        {
            "ok": False,
            "invented_items": ["изобретено в 1712 году без опоры"],
            "rationale": "Есть выдуманная дата.",
        }
    )
    out = soft_factcheck(dossier, llm=llm, auto_freeze=True)
    assert out.frozen is False
    assert out.soft_factcheck and out.soft_factcheck.ok is False
    with pytest.raises(ValueError, match="soft_factcheck.ok=False"):
        out.freeze()
