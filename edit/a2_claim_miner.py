"""EDIT-A2 · Майнер тезисов: source_map segment → list[ClaimCard]."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from edit.audience import load_audience
from edit.kie_client import load_llm_config
from edit.llm import ChatModel, get_chat_model, invoke_json
from models import ClaimCard, ScoredTopic, SourceMap, SourceSegment

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "a2_claim_miner.txt"
BOOK_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "a2_claim_miner_book.txt"
BOOK_PASS_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "a2_b1_book_pass.txt"


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def load_book_system_prompt() -> str:
    return BOOK_PROMPT_PATH.read_text(encoding="utf-8").strip()


def load_book_pass_prompt() -> str:
    return BOOK_PASS_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _normalize_quote_text(text: str) -> str:
    """Нормализация для OCR: пробелы, ё/е, типографика."""
    text = " ".join(text.split())
    text = text.replace("ё", "е").replace("Ё", "Е")
    for a, b in (
        ("—", "-"),
        ("–", "-"),
        ("«", '"'),
        ("»", '"'),
        ("“", '"'),
        ("”", '"'),
        ("’", "'"),
        ("…", "..."),
    ):
        text = text.replace(a, b)
    return text


def _quote_in_segment(quote: str, segment_text: str) -> bool:
    """Дословное присутствие цитаты (с нормализацией пробелов/OCR)."""
    norm_q = _normalize_quote_text(quote)
    norm_t = _normalize_quote_text(segment_text)
    if not norm_q:
        return False
    if norm_q in norm_t:
        return True
    # OCR иногда рвёт длинную цитату — достаточно ядра ≥40 символов.
    if len(norm_q) >= 48:
        core = norm_q[4:-4] if len(norm_q) > 56 else norm_q
        if len(core) >= 40 and core in norm_t:
            return True
    return False


def validate_claim_payload(
    raw: Any,
    segment: SourceSegment,
    *,
    require_quote_substring: bool = True,
) -> tuple[list[ClaimCard], list[str]]:
    """Парсит сырой JSON-элемент/список → валидные карточки; остальное логирует и отбрасывает."""
    if isinstance(raw, dict) and "cards" in raw:
        items = raw["cards"]
    elif isinstance(raw, list):
        items = raw
    else:
        return [], [f"ожидался JSON-массив ClaimCard, получено: {type(raw).__name__}"]

    accepted: list[ClaimCard] = []
    rejected: list[str] = []

    for i, item in enumerate(items):
        try:
            if not isinstance(item, dict):
                raise TypeError(f"элемент [{i}] не объект")
            # жёстко привязываем к сегменту — модель не выбирает чужой id
            item = {**item, "source_segment_id": segment.segment_id}
            # мягкие дефолты только для полей, которые модели часто забывают,
            # при живом claim/counter_expectation/visual_hint/citation
            item.setdefault("kind", "causal")
            item.setdefault("confidence", 0.65)
            item.setdefault("scope", {})
            if not item.get("object_anchor") and item.get("visual_hint"):
                item["object_anchor"] = item["visual_hint"]
            if "citation" in item and isinstance(item["citation"], dict):
                item["citation"] = {
                    **item["citation"],
                    "locator": item["citation"].get("locator") or segment.locator,
                }
            card = ClaimCard.model_validate(item)
            if require_quote_substring and not _quote_in_segment(card.citation.quote, segment.text):
                rejected.append(
                    f"[{i}] claim_id={card.claim_id}: citation.quote не найдена в сегменте"
                )
                continue
            accepted.append(card)
        except (ValidationError, TypeError, ValueError) as exc:
            rejected.append(f"[{i}] отброшена: {exc}")

    for msg in rejected:
        logger.warning("A2 hard-fail card: %s", msg)

    return accepted, rejected


def mine_claims_from_segment(
    segment: SourceSegment,
    *,
    llm: ChatModel | None = None,
    model: str | None = None,
    require_quote_substring: bool = True,
    json_retries: int | None = None,
) -> list[ClaimCard]:
    chat = llm or get_chat_model(temperature=0.0, model=model)
    retries = json_retries
    if retries is None:
        retries = int((load_llm_config().get("a1_a2_matrix") or {}).get("json_retries", 2))
    user = (
        f"segment_id: {segment.segment_id}\n"
        f"locator: {segment.locator}\n\n"
        f"<audience>\n{load_audience()}\n</audience>\n\n"
        f"<segment>\n{segment.text}\n</segment>"
    )
    raw = invoke_json(
        chat,
        [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user},
        ],
        retries=retries,
    )
    cards, _rejected = validate_claim_payload(
        raw, segment, require_quote_substring=require_quote_substring
    )
    return cards


def mine_claims(
    source_map: SourceMap,
    *,
    llm: ChatModel | None = None,
    model: str | None = None,
    require_quote_substring: bool = True,
    json_retries: int | None = None,
) -> list[ClaimCard]:
    """Прогон A2 по всем сегментам source_map."""
    out: list[ClaimCard] = []
    for segment in source_map.segments:
        out.extend(
            mine_claims_from_segment(
                segment,
                llm=llm,
                model=model,
                require_quote_substring=require_quote_substring,
                json_retries=json_retries,
            )
        )
    return out


def mine_claims_from_book(
    text: str,
    *,
    source_id: str = "book",
    title: str = "книга",
    llm: ChatModel | None = None,
    model: str | None = None,
    require_quote_substring: bool = True,
    json_retries: int | None = None,
    max_chars: int | None = None,
) -> list[ClaimCard]:
    """Один A2-вызов на всю книгу: дешевле, чем майнинг по сегментам.

    Книга ~100–200k токенов умещается в длинный контекст; платим за input
    один раз и получаем короткий shortlist, а не сотни карточек.
    """
    body = text.strip()
    if max_chars is not None and len(body) > max_chars:
        body = body[:max_chars]
    chat = llm or get_chat_model(temperature=0.0, model=model)
    retries = json_retries
    if retries is None:
        retries = int((load_llm_config().get("a1_a2_matrix") or {}).get("json_retries", 2))

    segment = SourceSegment(
        segment_id="book",
        locator=title,
        text=body,
        ordinal=0,
        heading=title,
    )
    user = (
        f"source_id: {source_id}\n"
        f"title: {title}\n"
        f"approx_tokens: {segment.token_estimate}\n\n"
        f"<audience>\n{load_audience()}\n</audience>\n\n"
        f"<book>\n{body}\n</book>"
    )
    raw = invoke_json(
        chat,
        [
            {"role": "system", "content": load_book_system_prompt()},
            {"role": "user", "content": user},
        ],
        retries=retries,
    )
    cards, _rejected = validate_claim_payload(
        raw, segment, require_quote_substring=require_quote_substring
    )
    return cards


def citation_hit_rate(
    cards: list[ClaimCard],
    source_map: SourceMap,
) -> dict[str, float | int]:
    """Доля карточек, чья quote дословно есть в исходном сегменте."""
    by_id = {s.segment_id: s for s in source_map.segments}
    if not cards:
        return {"total": 0, "hits": 0, "rate": 1.0}
    hits = 0
    for card in cards:
        seg = by_id.get(card.source_segment_id)
        if seg and _quote_in_segment(card.citation.quote, seg.text):
            hits += 1
    return {"total": len(cards), "hits": hits, "rate": hits / len(cards)}


def mine_and_score_book(
    text: str,
    *,
    source_id: str = "book",
    title: str = "книга",
    llm: ChatModel | None = None,
    model: str | None = None,
    require_quote_substring: bool = True,
    json_retries: int | None = None,
) -> tuple[list[ClaimCard], list[ScoredTopic]]:
    """Ровно один LLM-вызов: темы из книги + оценка привлекательности."""
    # локальный импорт: без циклического top-level с b1_topic_scoring
    from edit.b1_topic_scoring import (
        _AXES,
        _config,
        _drop,
        _total,
        claim_to_topic_candidate,
        gate_topic,
    )

    body = text.strip()
    chat = llm or get_chat_model(temperature=0.0, model=model)
    retries = json_retries
    if retries is None:
        retries = int((load_llm_config().get("a1_a2_matrix") or {}).get("json_retries", 2))

    segment = SourceSegment(
        segment_id="book",
        locator=title,
        text=body,
        ordinal=0,
        heading=title,
    )
    user = (
        f"source_id: {source_id}\n"
        f"title: {title}\n"
        f"approx_tokens: {segment.token_estimate}\n\n"
        f"<audience>\n{load_audience()}\n</audience>\n\n"
        f"<book>\n{body}\n</book>"
    )
    raw = invoke_json(
        chat,
        [
            {"role": "system", "content": load_book_pass_prompt()},
            {"role": "user", "content": user},
        ],
        retries=retries,
    )
    if isinstance(raw, dict):
        raw = raw.get("topics") or raw.get("cards") or raw.get("items") or []
    if not isinstance(raw, list):
        raise ValueError("book pass: ожидался JSON-массив тем")

    # topic_id в объединённом ответе = claim_id
    normalized = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        item = {**item}
        if not item.get("claim_id") and item.get("topic_id"):
            item["claim_id"] = item["topic_id"]
        if not item.get("topic_id") and item.get("claim_id"):
            item["topic_id"] = item["claim_id"]
        normalized.append(item)

    cards, _rejected = validate_claim_payload(
        normalized, segment, require_quote_substring=require_quote_substring
    )
    by_id = {card.claim_id: card for card in cards}
    cfg = _config()
    weights = {str(k): float(v) for k, v in (cfg.get("weights") or {}).items()}
    min_axis = int(cfg.get("min_axis_for_production", 2))
    soft_axes = {str(x) for x in (cfg.get("soft_axes") or ["showable"])}
    produce_threshold = float(cfg.get("produce_threshold", 3.4))
    scored: list[ScoredTopic] = []

    for item in normalized:
        topic_id = str(item.get("topic_id") or "")
        card = by_id.get(topic_id)
        if card is None:
            continue
        topic = claim_to_topic_candidate(card)
        failures = gate_topic(topic)
        if failures:
            scored.append(_drop(topic, failures))
            continue
        try:
            candidate = ScoredTopic(
                topic_id=topic.topic_id,
                gates_passed=True,
                gate_failures=[],
                **{axis: item.get(axis) for axis in _AXES},
                total=0.0,
                verdict="bank",
                one_line=topic.one_line,
            )
        except Exception:
            scored.append(_drop(topic, ["неполные оси оценки в ответе модели"]))
            continue
        total = _total(candidate, weights)
        hard_axes = [axis for axis in _AXES if axis not in soft_axes]
        low_axis = any(getattr(candidate, axis).value < min_axis for axis in hard_axes)
        verdict = "produce" if total >= produce_threshold and not low_axis else "bank"
        scored.append(candidate.model_copy(update={"total": total, "verdict": verdict}))

    scored = sorted(scored, key=lambda x: (-x.total, x.topic_id))
    return cards, scored
