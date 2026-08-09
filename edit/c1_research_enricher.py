"""C1.5 · LLM добывает доп. факты/уточнения из текста и web, не список дыр."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_personal_story_model
from models import Dossier, ResearchPack, StoryBrief

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "c1_research_enricher.txt"

_PRIMARY_URL = "local://primary"


def _normalize_gaps(gaps: object) -> list[str]:
    if not isinstance(gaps, list):
        return []
    normalized: list[str] = []
    for item in gaps:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            # Старые ответы иногда отдавали эссе про пробелы — сжимаем в query.
            topic = item.get("topic") or item.get("gap") or item.get("title") or ""
            query = item.get("query") or item.get("search") or ""
            text = str(query or topic).strip()
        else:
            text = str(item).strip()
        if text:
            normalized.append(text[:200])
        if len(normalized) >= 3:
            break
    return normalized


def _normalize_facts(facts: object) -> list[dict]:
    if not isinstance(facts, list):
        return []
    normalized: list[dict] = []
    for item in facts:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row.setdefault("fact", row.get("text") or row.get("detail") or "")
        row.setdefault(
            "why_it_matters",
            row.get("why") or row.get("reason") or "Усиливает proof_plan.",
        )
        row.setdefault(
            "source_url",
            row.get("url") or row.get("source") or "",
        )
        if isinstance(row.get("fact"), str):
            row["fact"] = row["fact"][:500]
        if isinstance(row.get("why_it_matters"), str):
            row["why_it_matters"] = row["why_it_matters"][:300]
        if isinstance(row.get("source_title"), str):
            row["source_title"] = row["source_title"][:200]
        elif not row.get("source_title"):
            row["source_title"] = ""
        normalized.append(row)
    return normalized


def _url_allowed(url: str, known_urls: set[str]) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    if raw == _PRIMARY_URL or raw.startswith("local://"):
        return True
    if raw in known_urls:
        return True
    try:
        host = urlparse(raw).netloc.lower()
    except Exception:
        return False
    if not host:
        return False
    for allowed in known_urls:
        try:
            if urlparse(allowed).netloc.lower() == host:
                return True
        except Exception:
            continue
    return False


def enrich_material(
    dossier: Dossier,
    brief: StoryBrief,
    *,
    llm: ChatModel | None = None,
) -> tuple[Dossier, ResearchPack]:
    """Добыть доп. факты из primary + web; gaps — только короткие search queries."""
    if dossier.frozen:
        raise ValueError("C1.5: dossier уже frozen")

    model = llm or get_personal_story_model(temperature=0.0)
    web_results = [
        item.model_dump(mode="json")
        for item in dossier.web_confirmations
        if item.supports_claim
    ]
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
                        "web_results": web_results,
                        "instruction": (
                            "Найди дополнительные данные/уточнения/мнения/факты по теме. "
                            "Не составляй список недостатков источника."
                        ),
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
    raw["gaps"] = _normalize_gaps(raw.get("gaps"))
    raw["facts"] = _normalize_facts(raw.get("facts"))
    pack = ResearchPack.model_validate(raw)

    known_urls = {item.url for item in dossier.web_confirmations if item.url}
    known_urls.add(_PRIMARY_URL)
    verified = [fact for fact in pack.facts if _url_allowed(fact.source_url, known_urls)]
    verified_pack = pack.model_copy(update={"facts": verified[:8], "gaps": pack.gaps[:3]})
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
