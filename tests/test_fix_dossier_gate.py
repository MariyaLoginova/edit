"""FIX-2: пустое досье не freeze; поиск unavailable ≠ empty."""

from __future__ import annotations

import pytest

from edit.c2_images import collect_images
from edit.c3_soft_factcheck import soft_factcheck
from edit.d2_prose import write_prose
from edit.search import NullSearcher, SearchUnavailableError
from models import (
    Dossier,
    ImageBuckets,
    ImageCandidate,
    SoftFactcheckResult,
    WebConfirmation,
    can_freeze,
)
from tests.claim_factory import make_countability_claim
from tests.fakes import FakeLLM, FakeSearcher
from edit.search import SearchHit


def _dossier_empty() -> Dossier:
    claim = make_countability_claim()
    return Dossier(claim_id=claim.claim_id, claim=claim)


def _img(url: str, state: str, query: str) -> ImageCandidate:
    return ImageCandidate(
        url=url, title=query, description=query, query=query, soft_match=True, for_state=state  # type: ignore[arg-type]
    )


def test_can_freeze_rejects_empty():
    d = _dossier_empty()
    ok, problems = can_freeze(d, min_images_per_state=3)
    assert ok is False
    assert any("material_notes" in p for p in problems)
    assert any("web_confirmation" in p for p in problems)


def test_search_unavailable_is_explicit():
    d = _dossier_empty()
    out = collect_images(d, searcher=NullSearcher())
    assert out.image_candidates.search_status == "unavailable"
    assert out.image_candidates.search_error
    with pytest.raises(SearchUnavailableError):
        NullSearcher().search_images("cat")


def test_c2_buckets_by_contrast_states():
    d = _dossier_empty()
    searcher = FakeSearcher(
        images=[
            SearchHit(url=f"https://img/{i}.jpg", title="кот улица", snippet="кот")
            for i in range(6)
        ]
    )
    out = collect_images(d, searcher=searcher)
    assert out.image_candidates.search_status == "ok"
    assert len(searcher.image_queries) == 2
    assert "один кот" in searcher.image_queries[0].lower() or "кот" in searcher.image_queries[0].lower()
    assert len(out.image_candidates.for_state_a) >= 1
    assert len(out.image_candidates.for_state_b) >= 1


def test_soft_factcheck_does_not_freeze_incomplete():
    claim = make_countability_claim()
    d = Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes="",
        web_confirmations=[],
        image_candidates=ImageBuckets(search_status="ok"),
    )
    out = soft_factcheck(d, llm=FakeLLM({"ok": True, "invented_items": [], "rationale": "ok"}))
    assert out.frozen is False
    assert out.freeze_blockers


def test_full_dossier_freezes():
    claim = make_countability_claim()
    pair = claim.contrast_pair
    d = Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes="счётность милоты на масштабе",
        web_confirmations=[
            WebConfirmation(url="https://ex.com", title="t", snippet="s", query="q")
        ],
        image_candidates=ImageBuckets(
            for_state_a=[_img(f"https://a/{i}.jpg", "a", pair.state_a) for i in range(3)],
            for_state_b=[_img(f"https://b/{i}.jpg", "b", pair.state_b) for i in range(3)],
            search_status="ok",
        ),
        soft_factcheck=SoftFactcheckResult(ok=True, rationale="ok"),
    )
    ok, problems = can_freeze(d, min_images_per_state=3)
    assert ok is True, problems
    frozen = d.freeze()
    assert frozen.frozen is True


def test_d2_hard_fails_on_incomplete_even_if_marked_frozen():
    claim = make_countability_claim()
    # обойти freeze() — собрать «вручную» frozen=True без материала
    d = Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes="",
        soft_factcheck=SoftFactcheckResult(ok=True, rationale="ok"),
        frozen=True,
        frozen_at="2026-01-01T00:00:00Z",
    )
    from models import Beat, BeatList, BeatRole

    beats = BeatList(
        script_id="s",
        claim_id=claim.claim_id,
        duration_sec=45,
        beats=[
            Beat(beat_id="b1", t_start=0, t_end=3, role=BeatRole.hook_evidence, claim_id=claim.claim_id),
            Beat(beat_id="b2", t_start=3, t_end=10, role=BeatRole.false_explanation, claim_id=claim.claim_id),
            Beat(beat_id="b3", t_start=10, t_end=26, role=BeatRole.contrast_ab, claim_id=claim.claim_id),
            Beat(beat_id="b4", t_start=26, t_end=38, role=BeatRole.mechanism, claim_id=claim.claim_id),
            Beat(beat_id="b5", t_start=38, t_end=45, role=BeatRole.coda, claim_id=claim.claim_id),
        ],
    )
    with pytest.raises(ValueError, match="неполное"):
        write_prose(d, beats, llm=FakeLLM({}))
