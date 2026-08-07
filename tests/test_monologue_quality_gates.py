from __future__ import annotations

from edit.e_check import _code_gates
from models import EndingType, MonologueDraft


def _draft(text: str) -> MonologueDraft:
    words = len(text.split())
    return MonologueDraft(
        claim_id="x",
        text=text,
        word_count=words,
        story_method="a_vot_nifiga",
        ending_type=EndingType.formula,
    )


def test_source_in_speech_is_blocked():
    text = (
        "Барби не придумали с нуля. " * 20
        + "Читаю у Горалик — и отвисает. "
        + "Поэтому я бы вернула Лилли в бельевой бренд."
    )
    issues = _code_gates(_draft(text))
    assert any("источник" in i.issue.lower() or "озвучке" in i.issue.lower() for i in issues)


def test_missing_idea_pitch_is_blocked():
    text = "Барби не придумали с нуля. " * 30
    issues = _code_gates(_draft(text))
    assert any("идеи" in i.issue.lower() or "питч" in i.issue.lower() for i in issues)


def test_clean_monologue_passes_code_gates():
    text = (
        "Барби не придумали с нуля — её поставили на детскую полку из магазина для взрослых. "
        "Создательница Барби с дочкой была в Европе и привезла оттуда куклу Лилли. "
        "Фигуру оставили, соски убрали. "
        "Поэтому я бы вернула Лилли в Agent Provocateur. "
        "Форма та же — меняется, кому она адресована."
    )
    # Добить до 120 слов без источников/дыр.
    text = text + (" И дальше ещё жёстче по деталям." * 20)
    assert _code_gates(_draft(text)) == []
