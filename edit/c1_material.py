"""C1 · Лёгкий сбор материала + веб-подтверждение тезиса."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from edit.config import load_thresholds
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from edit.search import SearchHit, WebSearcher, default_searcher
from models import ClaimCard, Dossier, WebConfirmation

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "c1_material.txt"


def _web_count() -> int:
    return int(load_thresholds().get("material", {}).get("web_results", 5))


def build_web_query(claim: ClaimCard) -> str:
    parts = [claim.claim]
    if claim.scope.author_or_work:
        parts.append(claim.scope.author_or_work)
    if claim.scope.period:
        parts.append(claim.scope.period)
    return " ".join(parts)


def _hits_to_confirmations(
    hits: list[SearchHit],
    query: str,
    support_flags: list[bool] | None = None,
) -> list[WebConfirmation]:
    out: list[WebConfirmation] = []
    for i, hit in enumerate(hits):
        if not hit.url:
            continue
        supports = True
        if support_flags is not None and i < len(support_flags):
            supports = bool(support_flags[i])
        out.append(
            WebConfirmation(
                url=hit.url,
                title=hit.title,
                snippet=hit.snippet,
                query=query,
                supports_claim=supports,
            )
        )
    return out


def _summarize_with_llm(
    claim: ClaimCard,
    hits: list[SearchHit],
    *,
    llm: ChatModel,
) -> tuple[str, list[bool]]:
    snippets = [
        {"i": i, "title": h.title, "snippet": h.snippet, "url": h.url}
        for i, h in enumerate(hits)
    ]
    user = (
        f"claim_id: {claim.claim_id}\n"
        f"claim: {claim.claim}\n"
        f"citation: {claim.citation.quote}\n\n"
        f"snippets: {snippets}"
    )
    response = llm.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": user},
        ]
    )
    raw = parse_json_payload(content_text(response))
    notes = str(raw.get("material_notes", "")).strip()
    flags = [bool(x) for x in raw.get("support_flags", [])]
    return notes, flags


def collect_material(
    claim: ClaimCard,
    *,
    searcher: WebSearcher | None = None,
    llm: ChatModel | None = None,
    existing: Dossier | None = None,
    primary_text: str = "",
    research_queries: list[str] | None = None,
) -> Dossier:
    """C1: поиск + опциональная LLM-выжимка → черновик Dossier (ещё не frozen)."""
    if existing is not None:
        existing.ensure_mutable()

    searcher = searcher or default_searcher()
    queries = list(dict.fromkeys(research_queries or [build_web_query(claim)]))
    hits = []
    hit_queries: list[str] = []
    for query in queries:
        found = searcher.search(query, max_results=_web_count())
        hits.extend(found)
        hit_queries.extend([query] * len(found))

    notes = ""
    flags: list[bool] | None = None
    if llm is not None and hits:
        try:
            notes, flags = _summarize_with_llm(claim, hits, llm=llm)
        except Exception:  # noqa: BLE001 — C1 деградация: оставляем сырые сниппеты
            logger.exception("C1 LLM summarize failed; keeping raw snippets")

    if not notes and hits:
        notes = " | ".join(
            f"{h.title}: {h.snippet}".strip(": ") for h in hits[:3] if h.title or h.snippet
        )

    confirmations = _hits_to_confirmations(hits, queries[0], flags)
    for confirmation, query in zip(confirmations, hit_queries):
        confirmation.query = query
    if primary_text:
        notes = (
            f"{notes}\n\nПЕРВИЧНЫЙ ТЕКСТ ИСТОЧНИКА:\n{primary_text.strip()}"
        ).strip()
    from models import ImageBuckets

    prev_images = (
        existing.image_candidates if existing is not None else ImageBuckets()
    )
    dossier = Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes=notes,
        web_confirmations=confirmations,
        image_candidates=prev_images,
        soft_factcheck=None,
        frozen=False,
    )
    return dossier
