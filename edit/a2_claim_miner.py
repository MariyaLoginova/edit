"""EDIT-A2 · Майнер тезисов: source_map segment → list[ClaimCard]."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import ClaimCard, SourceMap, SourceSegment

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "a2_claim_miner.txt"


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def _quote_in_segment(quote: str, segment_text: str) -> bool:
    """Дословное присутствие цитаты (с нормализацией пробелов)."""
    norm_q = " ".join(quote.split())
    norm_t = " ".join(segment_text.split())
    return bool(norm_q) and norm_q in norm_t


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
    require_quote_substring: bool = True,
) -> list[ClaimCard]:
    model = llm or get_chat_model(temperature=0.0)
    user = (
        f"segment_id: {segment.segment_id}\n"
        f"locator: {segment.locator}\n\n"
        f"<segment>\n{segment.text}\n</segment>"
    )
    response = model.invoke(
        [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user},
        ]
    )
    raw = parse_json_payload(content_text(response))
    cards, _rejected = validate_claim_payload(
        raw, segment, require_quote_substring=require_quote_substring
    )
    return cards


def mine_claims(
    source_map: SourceMap,
    *,
    llm: ChatModel | None = None,
    require_quote_substring: bool = True,
) -> list[ClaimCard]:
    """Прогон A2 по всем сегментам source_map."""
    out: list[ClaimCard] = []
    for segment in source_map.segments:
        out.extend(
            mine_claims_from_segment(
                segment,
                llm=llm,
                require_quote_substring=require_quote_substring,
            )
        )
    return out
