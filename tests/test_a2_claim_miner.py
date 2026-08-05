from __future__ import annotations

import json

from edit.a2_claim_miner import mine_claims, mine_claims_from_segment, validate_claim_payload
from models import ClaimKind, SourceSegment
from tests.fakes import FakeLLM


def _good_card(segment: SourceSegment, **overrides):
    quote = "the little black dress succeeded because it required almost no maintenance and looked correct from morning errands to evening"
    data = {
        "claim_id": "lbd-maintenance-not-luxury",
        "kind": "causal",
        "claim": "Маленькое чёрное взлетело как наряд без ухода, а не как символ роскоши",
        "counter_expectation": "Считают, что LBD — про вневременную элегантность и статус",
        "visual_hint": "Chanel little black dress, реклама Vogue 1926",
        "citation": {"locator": segment.locator, "quote": quote},
        "scope": {"period": "1920s", "region": "Paris", "author_or_work": "Chanel"},
        "source_segment_id": segment.segment_id,
        "confidence": 0.9,
    }
    data.update(overrides)
    return data


def test_validate_accepts_valid_and_drops_invalid(fashion_source):
    segment = fashion_source.segments[0]
    raw = [
        _good_card(segment),
        _good_card(
            segment,
            claim_id="bad-compound",
            claim="Первая причина; вторая причина в одном",
        ),
        _good_card(
            segment,
            claim_id="hallucinated-quote",
            citation={"locator": segment.locator, "quote": "этой цитаты нет в тексте сегмента совсем"},
        ),
        {
            "claim_id": "missing-fields",
            "kind": "causal",
            "claim": "что-то",
        },
    ]
    cards, rejected = validate_claim_payload(raw, segment)
    assert len(cards) == 1
    assert cards[0].claim_id == "lbd-maintenance-not-luxury"
    assert cards[0].kind is ClaimKind.causal
    assert len(rejected) == 3


def test_mine_claims_returns_at_least_three_on_fashion_fixture(fashion_source):
    segment = fashion_source.segments[0]
    quote2 = "black hid the dirt of the city commute better than pale silks of the salon"
    payload = [
        _good_card(segment),
        _good_card(
            segment,
            claim_id="lbd-black-hides-dirt",
            kind="corrective",
            claim="Чёрный маскировал городскую грязь лучше пастельного шёлка салона",
            counter_expectation="Чёрное читают как знак роскоши, не как практичный камуфляж",
            visual_hint="Уличное фото парижской коммютерши в чёрном платье, 1920s",
            citation={"locator": segment.locator, "quote": quote2},
            confidence=0.85,
        ),
        _good_card(
            segment,
            claim_id="lbd-factory-straight-cut",
            claim="Прямой крой упростил фабричный пошив готового платья",
            counter_expectation="Крой воспринимают как эстетический жест авангарда",
            visual_hint="Выкройка прямого LBD с фабричного лекала",
            citation={"locator": segment.locator, "quote": quote2},
            confidence=0.7,
        ),
    ]
    llm = FakeLLM(payload)
    cards = mine_claims(fashion_source, llm=llm)
    assert len(cards) >= 3
    assert all(c.kind in (ClaimKind.causal, ClaimKind.corrective, ClaimKind.origin) for c in cards)
    assert len(llm.calls) == 1


def test_biography_segment_yields_empty_when_model_respects_genre(biography_source):
    llm = FakeLLM([])
    cards = mine_claims(biography_source, llm=llm)
    assert cards == []


def test_claim_id_stable_across_two_runs(fashion_source):
    segment = fashion_source.segments[0]
    payload = [_good_card(segment)]
    a = mine_claims_from_segment(segment, llm=FakeLLM(payload))
    b = mine_claims_from_segment(segment, llm=FakeLLM(payload))
    assert [c.claim_id for c in a] == [c.claim_id for c in b]


def test_markdown_fenced_json_parsed(fashion_source):
    segment = fashion_source.segments[0]
    fenced = "```json\n" + json.dumps([_good_card(segment)], ensure_ascii=False) + "\n```"
    cards = mine_claims_from_segment(segment, llm=FakeLLM(fenced))
    assert len(cards) == 1
