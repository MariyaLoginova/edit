"""EDIT-A1 · Сегментация источника → SourceMap (preprocessing, почти без LLM)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from edit.kie_client import load_llm_config
from models import SegmentStrategy, SourceMap, SourceSegment

_CHAPTER_RE = re.compile(
    r"^(глава|chapter|часть|part)\s+[\dIVXLC]+([.:)\s].*)?$",
    re.IGNORECASE,
)
_MULTI_NL = re.compile(r"\n\s*\n+")


def estimate_tokens(text: str) -> int:
    """Грубая оценка: символы/4 (не tiktoken — достаточно для окон)."""
    return max(1, len(text.strip()) // 4) if text.strip() else 0


def _seg_cfg() -> dict[str, Any]:
    return (load_llm_config().get("segmentation") or {})


def _slug_source_id(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ_-]+", "-", raw.strip().lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "source"


def read_source_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _is_heading(line: str) -> bool:
    """Строгий heading: markdown / «Глава N» / SHORT ALL CAPS. Не soft-wrap строк."""
    t = line.strip()
    if not t or len(t) > 100:
        return False
    if t.startswith("#"):
        return True
    if _CHAPTER_RE.match(t):
        return True
    letters = [c for c in t if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(t.split()) <= 12:
        return True
    return False


def split_paragraphs(text: str) -> list[tuple[str | None, str]]:
    """→ список (heading|None, paragraph_text). Заголовок липнет к следующему абзацу."""
    normalized = text.replace("\r\n", "\n")
    chunks = [c.strip() for c in _MULTI_NL.split(normalized) if c.strip()]
    out: list[tuple[str | None, str]] = []
    pending_heading: str | None = None
    for chunk in chunks:
        # первая строка chunk может быть heading, остальное — тело с soft-wrap
        raw_lines = chunk.split("\n")
        lines = [ln.strip() for ln in raw_lines if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1 and _is_heading(lines[0]):
            pending_heading = lines[0].lstrip("#").strip()
            continue
        heading_here: str | None = None
        body_lines = lines
        if _is_heading(lines[0]) and len(lines) > 1:
            heading_here = lines[0].lstrip("#").strip()
            body_lines = lines[1:]
        body = " ".join(body_lines).strip()
        body = re.sub(r"\s+", " ", body)
        if not body:
            if heading_here:
                pending_heading = heading_here
            continue
        out.append((heading_here or pending_heading, body))
        pending_heading = None
    if pending_heading and not out:
        out.append((pending_heading, pending_heading))
    return out


def _build_segments(
    source_id: str,
    pairs: list[tuple[str | None, str]],
) -> list[SourceSegment]:
    segments: list[SourceSegment] = []
    for i, (heading, text) in enumerate(pairs):
        if not text.strip():
            continue
        segments.append(
            SourceSegment(
                segment_id=f"{source_id}-{i:04d}",
                text=text.strip(),
                ordinal=i,
                heading=heading,
                token_estimate=estimate_tokens(text),
                locator=heading or f"seg-{i}",
            )
        )
    return segments


def segment_paragraphs(
    text: str,
    *,
    source_id: str,
    title: str = "",
    language: str = "ru",
) -> SourceMap:
    pairs = split_paragraphs(text)
    return SourceMap(
        source_id=source_id,
        title=title,
        language=language,
        strategy=SegmentStrategy.paragraph,
        segments=_build_segments(source_id, pairs),
    )


def segment_semantic(
    text: str,
    *,
    source_id: str,
    title: str = "",
    language: str = "ru",
    max_tokens: int | None = None,
    min_tokens: int | None = None,
) -> SourceMap:
    """Склейка соседних абзацев до max_tokens; смена heading — жёсткая граница.

    Без эмбеддингов/LLM (тикет: начать с простого).
    """
    cfg = _seg_cfg()
    max_tok = max_tokens if max_tokens is not None else int(cfg.get("semantic_max_tokens", 500))
    min_tok = min_tokens if min_tokens is not None else int(cfg.get("semantic_min_tokens", 80))

    pairs = split_paragraphs(text)
    blocks: list[tuple[str | None, str]] = []
    buf_heading: str | None = None
    buf_parts: list[str] = []
    buf_tokens = 0

    def flush() -> None:
        nonlocal buf_heading, buf_parts, buf_tokens
        if not buf_parts:
            return
        blocks.append((buf_heading, "\n\n".join(buf_parts)))
        buf_heading, buf_parts, buf_tokens = None, [], 0

    for heading, para in pairs:
        tok = estimate_tokens(para)
        # новый заголовок при непустом буфере — граница темы
        if heading is not None and buf_parts and heading != buf_heading:
            flush()
        if not buf_parts:
            buf_heading = heading
            buf_parts = [para]
            buf_tokens = tok
            continue
        if buf_tokens + tok <= max_tok:
            buf_parts.append(para)
            buf_tokens += tok
            if heading and not buf_heading:
                buf_heading = heading
        else:
            # если буфер слишком мелкий — всё равно доклеим раз
            if buf_tokens < min_tok and buf_tokens + tok <= max_tok * 1.25:
                buf_parts.append(para)
                buf_tokens += tok
                flush()
            else:
                flush()
                buf_heading = heading
                buf_parts = [para]
                buf_tokens = tok
    flush()

    return SourceMap(
        source_id=source_id,
        title=title,
        language=language,
        strategy=SegmentStrategy.semantic,
        segments=_build_segments(source_id, blocks),
    )


def segment_fixed_window(
    text: str,
    *,
    source_id: str,
    title: str = "",
    language: str = "ru",
    window_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> SourceMap:
    cfg = _seg_cfg()
    win = window_tokens if window_tokens is not None else int(cfg.get("fixed_window_tokens", 450))
    overlap = (
        overlap_tokens
        if overlap_tokens is not None
        else int(cfg.get("fixed_window_overlap", 60))
    )
    if win < 50:
        raise ValueError("fixed_window_tokens слишком мал")
    if overlap >= win:
        raise ValueError("overlap должен быть < window")

    # токенизация грубая: режем по словам, ~1 слово ≈ 1 токен для окна
    words = re.findall(r"\S+\s*", text.strip())
    if not words:
        return SourceMap(
            source_id=source_id,
            title=title,
            language=language,
            strategy=SegmentStrategy.fixed_window,
            segments=[],
        )

    step = max(1, win - overlap)
    pairs: list[tuple[str | None, str]] = []
    start = 0
    while start < len(words):
        chunk = "".join(words[start : start + win]).strip()
        if chunk:
            pairs.append((None, chunk))
        if start + win >= len(words):
            break
        start += step

    return SourceMap(
        source_id=source_id,
        title=title,
        language=language,
        strategy=SegmentStrategy.fixed_window,
        segments=_build_segments(source_id, pairs),
    )


_STRATEGIES = {
    SegmentStrategy.paragraph: segment_paragraphs,
    SegmentStrategy.semantic: segment_semantic,
    SegmentStrategy.fixed_window: segment_fixed_window,
}


def segment_source(
    text: str,
    *,
    source_id: str,
    title: str = "",
    language: str = "ru",
    strategy: SegmentStrategy | str | None = None,
) -> SourceMap:
    if strategy is None:
        strategy = _seg_cfg().get("default_strategy") or SegmentStrategy.semantic
    strat = SegmentStrategy(strategy) if not isinstance(strategy, SegmentStrategy) else strategy
    fn = _STRATEGIES[strat]
    return fn(text, source_id=source_id, title=title, language=language)


def segment_file(
    path: Path,
    *,
    source_id: str | None = None,
    title: str | None = None,
    language: str = "ru",
    strategy: SegmentStrategy | str | None = None,
) -> SourceMap:
    path = Path(path)
    sid = source_id or _slug_source_id(path.stem)
    return segment_source(
        read_source_text(path),
        source_id=sid,
        title=title if title is not None else path.stem,
        language=language,
        strategy=strategy,
    )


def segment_all_strategies(
    text: str,
    *,
    source_id: str,
    title: str = "",
    language: str = "ru",
) -> dict[SegmentStrategy, SourceMap]:
    return {
        s: segment_source(
            text, source_id=source_id, title=title, language=language, strategy=s
        )
        for s in SegmentStrategy
    }
