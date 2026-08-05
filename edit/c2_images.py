"""C2 · Пачка картинок из веб-поиска; отбор/права — вне графа."""

from __future__ import annotations

from edit.config import load_thresholds
from edit.search import ImageSearcher, default_searcher, soft_metadata_match
from models import Dossier, ImageCandidate


def _image_count() -> int:
    return int(load_thresholds().get("material", {}).get("image_results", 8))


def build_image_query(dossier: Dossier) -> str:
    hint = dossier.claim.visual_hint.strip()
    if dossier.claim.scope.author_or_work:
        return f"{hint} {dossier.claim.scope.author_or_work}"
    return hint


def collect_images(
    dossier: Dossier,
    *,
    searcher: ImageSearcher | None = None,
    keep_non_matching: bool = True,
) -> Dossier:
    """C2: дополняет dossier.image_candidates. Не замораживает."""
    dossier.ensure_mutable()
    searcher = searcher or default_searcher()
    query = build_image_query(dossier)
    hits = searcher.search_images(query, max_results=_image_count())

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
            )
        )

    # предпочитаем soft_match=true в начале пачки
    candidates.sort(key=lambda c: (not c.soft_match, c.url))
    return dossier.model_copy(update={"image_candidates": candidates})
