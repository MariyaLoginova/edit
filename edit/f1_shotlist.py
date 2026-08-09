"""F1 · Раскадровка: каждая фраза → пачка картинок из веб-поиска."""

from __future__ import annotations

from edit.config import load_thresholds
from edit.search import ImageSearcher, default_searcher, soft_metadata_match
from models import Dossier, ScriptDraft, ShotImage, ShotList, ShotPacket


def _per_phrase() -> int:
    return int(load_thresholds().get("shots", {}).get("images_per_phrase", 5))


def build_phrase_query(phrase: str, dossier: Dossier) -> str:
    """Запрос: объект из visual_hint + ключевые слова фразы (без стоп-слов режем мягко)."""
    base = dossier.claim.visual_hint.strip()
    # короткая выжимка фразы
    words = [w for w in phrase.split() if len(w) > 3][:6]
    tail = " ".join(words)
    if dossier.claim.scope.author_or_work:
        return f"{base} {dossier.claim.scope.author_or_work} {tail}".strip()
    return f"{base} {tail}".strip()


def build_shotlist(
    script: ScriptDraft,
    dossier: Dossier,
    *,
    searcher: ImageSearcher | None = None,
) -> ShotList:
    if not dossier.frozen:
        raise ValueError("F1: досье должно быть заморожено")
    if script.claim_id != dossier.claim_id:
        raise ValueError("F1: script.claim_id != dossier.claim_id")

    searcher = searcher or default_searcher()
    n = _per_phrase()
    shots: list[ShotPacket] = []

    for line in script.lines:
        query = build_phrase_query(line.text, dossier)
        hits = searcher.search_images(query, max_results=n)
        images: list[ShotImage] = []
        for hit in hits:
            if not hit.url:
                continue
            images.append(
                ShotImage(
                    url=hit.url,
                    title=hit.title,
                    description=hit.snippet,
                    query=query,
                    soft_match=soft_metadata_match(query, hit.title, hit.snippet),
                )
            )
        images.sort(key=lambda img: (not img.soft_match, img.url))
        shots.append(
            ShotPacket(
                t_start=line.t_start,
                t_end=line.t_end,
                phrase=line.text,
                claim_id=line.claim_id or script.claim_id,
                query=query,
                images=images,
            )
        )

    return ShotList(script_id=script.script_id, claim_id=script.claim_id, shots=shots)
