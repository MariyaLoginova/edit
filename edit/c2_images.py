"""C2 · Картинки под state_a / state_b (FIX-2)."""

from __future__ import annotations

import logging

from edit.config import load_thresholds
from edit.search import (
    ImageSearcher,
    SearchUnavailableError,
    default_searcher,
    soft_metadata_match,
)
from models import Dossier, ImageBuckets, ImageCandidate

logger = logging.getLogger(__name__)


def _image_count() -> int:
    return int(load_thresholds().get("material", {}).get("image_results", 8))


def _hits_to_candidates(
    hits: list,
    query: str,
    *,
    for_state: str,
    keep_non_matching: bool,
) -> list[ImageCandidate]:
    candidates: list[ImageCandidate] = []
    for hit in hits:
        if not hit.url:
            continue
        matched = soft_metadata_match(query, hit.title, hit.snippet)
        if not matched and not keep_non_matching:
            continue
        candidates.append(
            ImageCandidate(
                url=hit.url,
                title=hit.title,
                description=hit.snippet,
                query=query,
                soft_match=matched,
                for_state=for_state,  # type: ignore[arg-type]
            )
        )
    candidates.sort(key=lambda c: (not c.soft_match, c.url))
    return candidates


def collect_images(
    dossier: Dossier,
    *,
    searcher: ImageSearcher | None = None,
    keep_non_matching: bool = True,
) -> Dossier:
    """C2: пачки под contrast_pair.state_a / state_b. Не замораживает."""
    dossier.ensure_mutable()
    searcher = searcher or default_searcher()
    pair = dossier.claim.contrast_pair
    n = _image_count()

    try:
        hits_a = searcher.search_images(pair.state_a, max_results=n)
        hits_b = searcher.search_images(pair.state_b, max_results=n)
    except SearchUnavailableError as exc:
        logger.error("C2: поиск не отработал: %s", exc)
        buckets = ImageBuckets(
            for_state_a=[],
            for_state_b=[],
            search_status="unavailable",
            search_error=str(exc),
        )
        return dossier.model_copy(update={"image_candidates": buckets})

    for_a = _hits_to_candidates(
        hits_a, pair.state_a, for_state="a", keep_non_matching=keep_non_matching
    )
    for_b = _hits_to_candidates(
        hits_b, pair.state_b, for_state="b", keep_non_matching=keep_non_matching
    )
    status = "empty" if (not for_a and not for_b) else "ok"
    if status == "empty":
        logger.warning(
            "C2: поиск отработал, но нашёл 0 картинок (state_a=%r state_b=%r)",
            pair.state_a,
            pair.state_b,
        )
    buckets = ImageBuckets(
        for_state_a=for_a,
        for_state_b=for_b,
        search_status=status,
        search_error=None,
    )
    return dossier.model_copy(update={"image_candidates": buckets})
