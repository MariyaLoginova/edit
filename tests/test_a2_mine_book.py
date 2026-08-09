from __future__ import annotations

from edit.a2_claim_miner import mine_claims_from_book
from tests.fakes import FakeLLM


def test_mine_claims_from_book_one_call():
    card = {
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
    }
    book = (
        "Окрашивание в черное. Кстати, следует заметить, что в реальной "
        "красильной мастерской XIV века чаны с этими двумя красками не могли бы "
        "находиться в одном помещении. Далее длинный текст книги."
    )
    llm = FakeLLM([card])
    claims = mine_claims_from_book(book, llm=llm, title="Пастуро")
    assert len(llm.calls) == 1
    assert "<book>" in llm.calls[0][1]["content"]
    assert len(claims) == 1
    assert claims[0].claim_id == "black-dye-guild-split"
