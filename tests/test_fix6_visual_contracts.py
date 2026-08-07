from __future__ import annotations

import pytest

from edit.d2_monologue import write_monologue
from edit.e_editor import _validate_visual_contract
from models import EndingType, ReelFormat
from tests.brief_factory import make_argument_brief, make_excursion_brief
from tests.claim_factory import make_frozen_dossier
from tests.fakes import FakeLLM


def test_motive_thesis_is_allowed_when_visual_story_holds():
    brief = make_argument_brief(
        main_thought="Карьерные Барби были репутационным щитом Mattel."
    )
    source = "твидовый костюм; длинные перчатки; разноцветных динозавриков"
    _validate_visual_contract(brief, source)


def test_chronology_angle_is_rejected():
    brief = make_argument_brief(angle="хронология 1960 → потом армия → потом палеонтолог")
    source = "твидовый костюм; длинные перчатки; разноцветных динозавриков"
    with pytest.raises(ValueError, match="хронолог"):
        _validate_visual_contract(brief, source)


def test_proof_quote_must_be_verbatim_in_primary_source():
    brief = make_argument_brief()
    source = "твидовый костюм; длинные перчатки"
    with pytest.raises(ValueError, match="source_quote"):
        _validate_visual_contract(brief, source)


def test_conclusion_quote_must_be_in_primary_source():
    brief = make_argument_brief()
    # conclusion.source_quote = твидовый костюм — ok; swap to missing
    brief.conclusion.source_quote = "этой фразы нет в источнике"
    source = "твидовый костюм; длинные перчатки; разноцветных динозавриков"
    with pytest.raises(ValueError, match="conclusion.source_quote"):
        _validate_visual_contract(brief, source)


def test_proof_quote_accepts_guillemets_vs_ascii_quotes():
    from edit.e_editor import _locate_source_quote

    source = 'манера изображать "дамочек" в комиксах 50-х годов'
    quote = "манера изображать «дамочек» в комиксах 50-х годов"
    assert _locate_source_quote(quote, source) == 'манера изображать "дамочек" в комиксах 50-х годов'


def test_d2_retries_until_monologue_is_in_fixed_word_range():
    dossier = make_frozen_dossier()
    brief = make_argument_brief()
    first = " ".join(["коротко"] * 90)
    valid = " ".join(["текст"] * 220) + " Спиздели или вдохновились?"
    calls = 0

    def router(messages):
        nonlocal calls
        calls += 1
        return first if calls == 1 else valid

    monologue = write_monologue(dossier, brief, llm=FakeLLM(router))
    assert 200 <= monologue.word_count <= 300
    assert "?" in monologue.text
    assert monologue.ending_type == EndingType.reactive
    assert monologue.format == ReelFormat.argument
    assert calls == 2


def test_excursion_needs_six_to_ten_exhibits():
    with pytest.raises(ValueError, match="6–10"):
        make_excursion_brief(exhibits=make_excursion_brief().exhibits[:3])
