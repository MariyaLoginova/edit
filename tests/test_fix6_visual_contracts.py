from __future__ import annotations

import pytest

from edit.d2_monologue import write_monologue
from edit.e_editor import _validate_visual_contract
from models import EndingType, ProofItem, StoryBrief
from tests.claim_factory import make_frozen_dossier
from tests.fakes import FakeLLM


def _brief(
    *,
    main_thought: str = "Костюм показывает разрешённый образ работы.",
    angle: str = "уменьшить до минимума — вся история в перчатках",
    why_viewer: str = "Ты тоже одеваешь «разрешённый» силуэт на собеседовании.",
) -> StoryBrief:
    source_quotes = ("твидовый костюм", "длинные перчатки", "разноцветных динозавриков")
    return StoryBrief(
        claim_id="x",
        main_thought=main_thought,
        angle=angle,
        why_viewer=why_viewer,
        visual_evidence="твидовый костюм, длинные перчатки и разноцветных динозавриков",
        recommended_method="a_vot_nifiga",
        alternative_methods=[],
        opening="Кадр ломает ожидание.",
        audience_reason=why_viewer,
        share_reason="Есть конкретный образ.",
        proof_plan=[
            ProofItem(point=f"деталь {i}", source_quote=quote)
            for i, quote in enumerate(source_quotes, start=1)
        ],
        idea_pitch="Я бы поставила эти костюмы в один ряд.",
        selected_structure="none",
        ending_type=EndingType.formula,
    )


def test_motive_thesis_is_allowed_when_visual_story_holds():
    """FIX-7: мотивный тезис больше не режется кодом — рамка шире."""
    brief = _brief(main_thought="Карьерные Барби были репутационным щитом Mattel.")
    source = "твидовый костюм; длинные перчатки; разноцветных динозавриков"
    _validate_visual_contract(brief, source)


def test_chronology_angle_is_rejected():
    brief = _brief(angle="хронология 1960 → потом армия → потом палеонтолог")
    source = "твидовый костюм; длинные перчатки; разноцветных динозавриков"
    with pytest.raises(ValueError, match="хронолог"):
        _validate_visual_contract(brief, source)


def test_proof_quote_must_be_verbatim_in_primary_source():
    brief = _brief()
    source = "твидовый костюм; длинные перчатки"
    with pytest.raises(ValueError, match="source_quote"):
        _validate_visual_contract(brief, source)


def test_proof_quote_accepts_guillemets_vs_ascii_quotes():
    from edit.e_editor import _locate_source_quote

    source = 'манера изображать "дамочек" в комиксах 50-х годов'
    quote = "манера изображать «дамочек» в комиксах 50-х годов"
    assert _locate_source_quote(quote, source) == 'манера изображать "дамочек" в комиксах 50-х годов'


def test_d2_retries_until_monologue_is_in_fixed_word_range():
    dossier = make_frozen_dossier()
    brief = _brief()
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
    assert calls == 2
