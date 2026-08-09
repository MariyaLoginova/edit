from __future__ import annotations

from edit.d1_visual_planner import _normalize_quote, _quote_in_haystack


def test_ocr_page_header_does_not_break_quote_match():
    source = (
        "Реклама спрашивала: «Скажи мне, какого цвета белье...» "
        "и так чёрное вытеснило белое."
    )
    # Модель иногда вставляет колонтитул OCR в середину цитаты.
    quote = (
        "Реклама спрашивала: «Скажи мне, какого цвета 134 Все оттенки черного "
        "белье...» и так чёрное вытеснило белое."
    )
    assert _quote_in_haystack(_normalize_quote(quote), _normalize_quote(source))
