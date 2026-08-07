from __future__ import annotations

from edit.b1_topic_scoring import score_topics
from models import TopicCandidate
from tests.fakes import FakeLLM


def _topic(topic_id: str = "strong") -> TopicCandidate:
    return TopicCandidate(
        topic_id=topic_id,
        one_line="Известная кукла пришла из взрослого комикса.",
        naive_expectation="Барби придумали как детскую игрушку.",
        source_conclusion_quote="первая Барби оказалась почти точной копией Лилли",
        visual_examples=["комикс", "Лилли", "упаковка", "витрина", "Барби", "реклама"],
    )


def _axes(topic_id: str, *, showable: int = 5):
    return {
        "topic_id": topic_id,
        "showable": {"value": showable, "why": "Есть ряд разных архивных объектов."},
        "surprise": {"value": 5, "why": "Детский символ имеет взрослый прообраз."},
        "recognizable": {"value": 5, "why": "Барби узнаваема далеко за ядром."},
        "social_currency": {"value": 4, "why": "Факт хочется пересказать."},
        "arguable": {"value": 3, "why": "Есть спор о заимствовании."},
        "supersystem": {"value": 4, "why": "Это про смену аудитории массового образа."},
    }


def test_b1_batches_only_topics_that_pass_code_gates():
    good = _topic()
    no_conclusion = _topic("no-conclusion").model_copy(
        update={"source_conclusion_quote": ""}
    )
    universal = _topic("universal").model_copy(
        update={"one_line": "Любой визуал отражает общество."}
    )
    llm = FakeLLM([_axes("strong")])
    scored = score_topics([good, no_conclusion, universal], llm=llm)
    assert len(llm.calls) == 1
    assert scored[0].topic_id == "strong"
    assert scored[0].verdict == "produce"
    assert {item.topic_id for item in scored if item.verdict == "drop"} == {
        "no-conclusion",
        "universal",
    }


def test_low_single_axis_sends_topic_to_bank_despite_high_total():
    topic = _topic()
    item = _axes("strong", showable=1)
    result = score_topics([topic], llm=FakeLLM([item]))
    assert result[0].total > 3
    assert result[0].verdict == "bank"


def test_b1_scores_batch_of_twenty_in_one_call():
    topics = [_topic(f"topic-{i}") for i in range(20)]
    response = [_axes(topic.topic_id) for topic in topics]
    llm = FakeLLM(response)
    result = score_topics(topics, llm=llm)
    assert len(llm.calls) == 1
    assert len(result) == 20
