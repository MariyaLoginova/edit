from __future__ import annotations

from edit.a2_claim_miner import mine_and_score_book
from tests.fakes import FakeLLM


def test_mine_and_score_book_is_one_llm_call():
    item = {
        "topic_id": "black-dye-guild-split",
        "claim_id": "black-dye-guild-split",
        "kind": "origin",
        "claim": "В XIV веке два способа получить чёрный нельзя было держать в одной мастерской.",
        "counter_expectation": "Чёрный — один цвет в палитре красильщика.",
        "visual_hint": "чаны красильщиков",
        "object_anchor": "чаны с двумя чёрными красками",
        "contrast_pair": {
            "state_a": "два красителя в одном помещении",
            "state_b": "цеха разделены",
            "shift": "цвет становится режимом труда",
        },
        "mechanism_term": "цвет-как-цех",
        "mechanism_explain": "Регламент делит ремесло по красителям.",
        "citation": {
            "locator": "Окрашивание",
            "quote": "чаны с этими двумя красками не могли бы находиться в одном помещении",
        },
        "scope": {"period": "XIV", "region": "Европа"},
        "source_segment_id": "book",
        "confidence": 0.9,
        "showable": {"value": 3, "why": "есть мастерские"},
        "surprise": {"value": 5, "why": "цвет = запрет"},
        "recognizable": {"value": 4, "why": "чёрный знаком"},
        "social_currency": {"value": 5, "why": "хочется переслать"},
        "arguable": {"value": 3, "why": "спор о регламенте"},
        "supersystem": {"value": 4, "why": "цвет как институт"},
    }
    book = (
        "Окрашивание в черное. Кстати, следует заметить, что в реальной "
        "красильной мастерской XIV века чаны с этими двумя красками не могли бы "
        "находиться в одном помещении."
    )
    llm = FakeLLM([item])
    claims, scored = mine_and_score_book(book, llm=llm, title="Пастуро")
    assert len(llm.calls) == 1
    assert len(claims) == 1
    assert scored[0].verdict == "produce"
    assert scored[0].total > 3
