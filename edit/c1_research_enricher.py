"""C1.5 · LLM отбирает web-факты, которые реально усиливают сценарий."""

from __future__ import annotations

from pathlib import Path

from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_personal_story_model
from models import Dossier, ResearchPack, StoryBrief

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "c1_research_enricher.txt"


def enrich_material(
    dossier: Dossier,
    brief: StoryBrief,
    *,
    llm: ChatModel | None = None,
) -> tuple[Dossier, ResearchPack]:
    """Добавляет в material_notes только факты, привязанные к web confirmation."""
    if dossier.frozen:
        raise ValueError("C1.5: dossier уже frozen")
    model = llm or get_personal_story_model(temperature=0.0)
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {
                "role": "user",
                "content": str(
                    {
                        "claim_id": dossier.claim_id,
                        "primary_text": dossier.material_notes,
                        "story_brief": brief.model_dump(mode="json"),
                        "web_results": [
                            item.model_dump(mode="json")
                            for item in dossier.web_confirmations
                            if item.supports_claim
                        ],
                    }
                ),
            },
        ]
    )
    raw = parse_json_payload(content_text(response))
    if not isinstance(raw, dict):
        raise ValueError("C1.5: ожидался JSON-объект")
    raw.setdefault("claim_id", dossier.claim_id)
    raw.setdefault("summary", "Исследователь не дал резюме.")
    pack = ResearchPack.model_validate(raw)

    known_urls = {item.url for item in dossier.web_confirmations}
    verified = [fact for fact in pack.facts if fact.source_url in known_urls]
    verified_pack = pack.model_copy(update={"facts": verified})
    if not verified:
        return dossier, verified_pack

    additions = "\n".join(
        f"- {fact.fact} [{fact.source_title or fact.source_url}] — {fact.why_it_matters}"
        for fact in verified
    )
    enriched = dossier.model_copy(
        update={
            "material_notes": (
                f"{dossier.material_notes}\n\nДОПОЛНИТЕЛЬНЫЕ ПРОВЕРЯЕМЫЕ ФАКТЫ:\n{additions}"
            )
        }
    )
    return enriched, verified_pack
