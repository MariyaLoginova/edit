from __future__ import annotations

from pathlib import Path

from edit.a1_segment import (
    estimate_tokens,
    segment_all_strategies,
    segment_file,
    segment_source,
)
from models import SegmentStrategy, SourceMap

SAMPLE = Path(__file__).resolve().parents[1] / "sources" / "sample-little-black-dress.txt"


def test_estimate_tokens_rough():
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 40) == 10


def test_paragraph_stable_ids():
    text = SAMPLE.read_text(encoding="utf-8")
    a = segment_source(text, source_id="sample-lbd", strategy=SegmentStrategy.paragraph)
    b = segment_source(text, source_id="sample-lbd", strategy=SegmentStrategy.paragraph)
    assert a.strategy == SegmentStrategy.paragraph
    assert len(a.segments) >= 3
    assert [s.segment_id for s in a.segments] == [s.segment_id for s in b.segments]
    assert [s.ordinal for s in a.segments] == list(range(len(a.segments)))
    assert a.segments[0].segment_id == "sample-lbd-0000"
    # «Глава 2…» — heading; soft-wrap строки абзаца heading'ом не становятся
    assert a.segments[0].heading and a.segments[0].heading.lower().startswith("глава")
    assert "элегантности" in a.segments[0].text or "little black" in a.segments[0].text.lower()
    SourceMap.model_validate(a.model_dump())


def test_semantic_merges_short_paragraphs():
    text = SAMPLE.read_text(encoding="utf-8")
    para = segment_source(text, source_id="sample-lbd", strategy="paragraph")
    sem = segment_source(text, source_id="sample-lbd", strategy="semantic")
    assert sem.strategy == SegmentStrategy.semantic
    assert 1 <= len(sem.segments) <= len(para.segments)
    assert all(s.token_estimate > 0 for s in sem.segments)


def test_fixed_window_overlap_coverage():
    text = SAMPLE.read_text(encoding="utf-8")
    win = segment_source(text, source_id="sample-lbd", strategy="fixed_window")
    assert win.strategy == SegmentStrategy.fixed_window
    assert len(win.segments) >= 1
    joined = " ".join(s.text for s in win.segments)
    assert "little black dress" in joined.lower() or "маленьк" in joined.lower()


def test_segment_file_and_all_strategies():
    maps = segment_all_strategies(
        SAMPLE.read_text(encoding="utf-8"),
        source_id="sample-lbd",
        title="LBD",
        language="ru",
    )
    assert set(maps) == set(SegmentStrategy)
    sm = segment_file(SAMPLE, source_id="sample-lbd", language="ru", strategy="paragraph")
    assert sm.source_id == "sample-lbd"
    assert sm.language == "ru"


def test_fixture_sourcemap_still_loads(fashion_source: SourceMap):
    assert fashion_source.segments
    assert fashion_source.segments[0].locator
    assert fashion_source.strategy in SegmentStrategy
