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
    if not brief.needs_external_research:
        return dossier, ResearchPack(
            claim_id=dossier.claim_id,
            facts=[],
            gaps=[],
            summary="C1.5 пропущен: визуальный тезис полностью опирается на первичный текст.",
        )
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
    if isinstance(raw.get("summary"), str):
        raw["summary"] = raw["summary"][:800]
    gaps = raw.get("gaps")
    if isinstance(gaps, list):
        normalized_gaps = []
        for item in gaps:
            if isinstance(item, str):
                normalized_gaps.append(item)
            elif isinstance(item, dict):
                topic = item.get("topic") or item.get("gap") or item.get("title") or ""
                why = (
                    item.get("why_needed")
                    or item.get("why")
                    or item.get("reason")
                    or item.get("detail")
                    or ""
                )
                text = ": ".join(part for part in (str(topic).strip(), str(why).strip()) if part)
                if text:
                    normalized_gaps.append(text)
            else:
                normalized_gaps.append(str(item))
        raw["gaps"] = normalized_gaps
    facts = raw.get("facts")
    if isinstance(facts, list):
        normalized_facts = []
        for item in facts:
            if not isinstance(item, dict):
                continue
            item = dict(item)
            item.setdefault("fact", item.get("text") or item.get("detail") or "")
            item.setdefault(
                "why_it_matters",
                item.get("why") or item.get("reason") or "Усиливает proof_plan.",
            )
            item.setdefault(
                "source_url",
                item.get("url") or item.get("source") or "",
            )
            if isinstance(item.get("fact"), str):
                item["fact"] = item["fact"][:500]
            if isinstance(item.get("why_it_matters"), str):
                item["why_it_matters"] = item["why_it_matters"][:300]
            normalized_facts.append(item)
        raw["facts"] = normalized_facts
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
