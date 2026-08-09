from __future__ import annotations

from edit.b1_topic_scoring import (
    claim_to_topic_candidate,
    gate_topic,
    score_mined_claims,
    score_topics,
)
from models import (
    Citation,
    ClaimCard,
    ClaimKind,
    ContrastPair,
    Scope,
    TopicCandidate,
)
from tests.fakes import FakeLLM


def _topic(topic_id: str = "strong") -> TopicCandidate:
    return TopicCandidate(
        topic_id=topic_id,
        one_line="Известная кукла пришла из взрослого комикса.",
        naive_expectation="Барби придумали как детскую игрушку.",
        source_conclusion_quote="первая Барби оказалась почти точной копией Лилли",
        visual_examples=["комикс", "Лилли", "упаковка", "витрина", "Барби", "реклама"],
    )


def _claim(claim_id: str = "lilli-origin") -> ClaimCard:
    return ClaimCard(
        claim_id=claim_id,
        kind=ClaimKind.origin,
        claim="Барби скопировали с немецкой Лилли из комикса.",
        counter_expectation="Барби придумали как детскую игрушку.",
        visual_hint="Bild Lilli",
        object_anchor="первая Барби OSS",
        contrast_pair=ContrastPair(
            state_a="комиксная Лилли для взрослых",
            state_b="детская Барби на полке",
            shift="взрослый прообраз стал детским символом",
        ),
        mechanism_term="смена аудитории",
        mechanism_explain="Образ переехал из взрослого рынка в детский без смены силуэта.",
        citation=Citation(locator="гл. 3", quote="почти точной копией Лилли"),
        scope=Scope(period="1950-е", region="США/ФРГ"),
        source_segment_id="seg-1",
        confidence=0.8,
    )


def _axes(topic_id: str, *, showable: int = 5, surprise: int = 5):
    return {
        "topic_id": topic_id,
        "showable": {"value": showable, "why": "Есть ряд разных архивных объектов."},
        "surprise": {"value": surprise, "why": "Детский символ имеет взрослый прообраз."},
        "recognizable": {"value": 5, "why": "Барби узнаваема далеко за ядром."},
        "social_currency": {"value": 4, "why": "Факт хочется пересказать."},
        "arguable": {"value": 3, "why": "Есть спор о заимствовании."},
        "supersystem": {"value": 4, "why": "Это про смену аудитории массового образа."},
    }


def test_author_quote_and_few_visuals_are_not_hard_gates():
    thin = _topic("thin").model_copy(
        update={"source_conclusion_quote": "", "visual_examples": ["один кадр"]}
    )
    assert gate_topic(thin) == []


def test_b1_batches_only_topics_that_pass_code_gates():
    good = _topic()
    no_conclusion = _topic("no-conclusion").model_copy(
        update={"source_conclusion_quote": "", "visual_examples": []}
    )
    universal = _topic("universal").model_copy(
        update={"one_line": "Любой визуал отражает общество."}
    )
    llm = FakeLLM([_axes("strong"), _axes("no-conclusion")])
    scored = score_topics([good, no_conclusion, universal], llm=llm)
    assert len(llm.calls) == 1
    assert {item.topic_id for item in scored if item.verdict == "drop"} == {"universal"}
    assert {item.topic_id for item in scored if item.verdict != "drop"} == {
        "strong",
        "no-conclusion",
    }


def test_low_showable_does_not_bank_when_soft_axis():
    topic = _topic()
    item = _axes("strong", showable=1)
    result = score_topics([topic], llm=FakeLLM([item]))
    assert result[0].showable.value == 1
    assert result[0].verdict == "produce"


def test_low_hard_axis_still_banks():
    topic = _topic()
    item = _axes("strong", surprise=1)
    result = score_topics([topic], llm=FakeLLM([item]))
    assert result[0].verdict == "bank"


def test_claim_to_topic_and_first_pass_scoring():
    claim = _claim()
    topic = claim_to_topic_candidate(claim)
    assert topic.topic_id == "lilli-origin"
    assert "Bild Lilli" in topic.visual_examples
    result = score_mined_claims([claim], llm=FakeLLM([_axes("lilli-origin")]))
    assert result[0].verdict == "produce"
    assert result[0].total > 3


def test_b1_scores_batch_of_twenty_in_one_call():
    topics = [_topic(f"topic-{i}") for i in range(20)]
    response = [_axes(topic.topic_id) for topic in topics]
    llm = FakeLLM(response)
    result = score_topics(topics, llm=llm)
    assert len(llm.calls) == 1
    assert len(result) == 20
