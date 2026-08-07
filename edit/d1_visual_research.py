"""D1.4: внешний визуальный ресёрч до монтажа D1.5."""

from __future__ import annotations

from pathlib import Path

from edit.llm import ChatModel, invoke_json
from edit.model_routing import get_personal_story_model
from edit.search import ImageSearcher, SearchUnavailableError, WebSearcher, default_searcher
from models import (
    Dossier,
    StoryBrief,
    VisualReference,
    VisualResearchFinding,
    VisualResearchPack,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d1_visual_research.txt"


def _refs(hits) -> list[VisualReference]:
    return [
        VisualReference(url=hit.url, title=hit.title, description=hit.snippet)
        for hit in hits
        if hit.url
    ]


def research_visual_material(
    dossier: Dossier,
    brief: StoryBrief,
    *,
    primary_text: str = "",
    searcher: WebSearcher | ImageSearcher | None = None,
    llm: ChatModel | None = None,
) -> VisualResearchPack:
    """Сначала найти историю исходного объекта, затем — референсы к плану."""
    if not dossier.frozen:
        raise ValueError("D1.4: нужен frozen dossier")
    model = llm or get_personal_story_model(temperature=0.1)
    raw = invoke_json(
        model,
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {
                "role": "user",
                "content": str(
                    {
                        "claim_id": dossier.claim_id,
                        "story_brief_for_speech": brief.for_d2(),
                        "primary_text": (primary_text or dossier.material_notes)[:18000],
                        "materials": dossier.material_notes[:9000],
                    }
                ),
            },
        ],
        retries=1,
    )
    if not isinstance(raw, dict):
        raise ValueError("D1.4: ожидался JSON VisualResearchPack")
    raw.setdefault("claim_id", dossier.claim_id)
    pack = VisualResearchPack.model_validate(raw)
    if pack.claim_id != dossier.claim_id:
        raise ValueError("D1.4: claim_id visual research не совпадает с досье")

    client = searcher or default_searcher()
    findings: list[VisualResearchFinding] = []
    try:
        for item in pack.queries:
            # Объект реализует оба протокола (Brave / тестовый FakeSearcher).
            web_hits = client.search(item.query, max_results=3)  # type: ignore[attr-defined]
            image_hits = client.search_images(item.query, max_results=5)  # type: ignore[attr-defined]
            findings.append(
                VisualResearchFinding(
                    query=item.query,
                    purpose=item.purpose,
                    web_references=_refs(web_hits),
                    image_references=_refs(image_hits),
                )
            )
    except (SearchUnavailableError, AttributeError) as exc:
        return pack.model_copy(
            update={"search_status": "unavailable", "search_error": str(exc)}
        )
    found = sum(
        len(item.web_references) + len(item.image_references) for item in findings
    )
    return pack.model_copy(
        update={
            "findings": findings,
            "search_status": "ok" if found else "empty",
            "search_error": None,
        }
    )
