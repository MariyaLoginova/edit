"""EDIT-A2 · Майнер тезисов: source_map segment → list[ClaimCard]."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from edit.audience import load_audience
from edit.kie_client import load_llm_config
from edit.llm import ChatModel, get_chat_model, invoke_json
from models import ClaimCard, SourceMap, SourceSegment

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "a2_claim_miner.txt"


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


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
