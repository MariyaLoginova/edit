"""C1.5 · Gemini + googleSearch: новые материалы по теме, не пересказ статьи."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from edit.kie_client import GOOGLE_SEARCH_TOOL, load_llm_config
from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_research_enrich_model
from models import Dossier, ResearchPack, StoryBrief

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "c1_research_enricher.txt"

_PRIMARY_URL = "local://primary"
_PRIMARY_CLIP = 14000


def _clip(text: str, limit: int = _PRIMARY_CLIP) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n\n… [{len(text) - limit} chars truncated]"


def _normalize_gaps(gaps: object) -> list[str]:
    if not isinstance(gaps, list):
        return []
    normalized: list[str] = []
    for item in gaps:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
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


def _is_http_url(url: str) -> bool:
    try:
        parsed = urlparse((url or "").strip())
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _research_settings() -> tuple[bool, float]:
    cfg = load_llm_config()
    web = bool(cfg.get("research_enrich_web_search", True))
    timeout = float(cfg.get("research_enrich_timeout_sec") or 360)
    return web, timeout


def _invoke_pack(
    *,
    model: ChatModel,
    dossier: Dossier,
    brief: StoryBrief,
    repair_note: str = "",
    use_web_search: bool = True,
    timeout: float = 360.0,
) -> ResearchPack:
    primary = _clip(dossier.material_notes)
    payload: dict = {
        "claim_id": dossier.claim_id,
        "primary_text": primary,
        "story_brief": {
            "main_thought": brief.main_thought,
            "angle": brief.angle,
            "opening": brief.opening,
            "research_queries": list(brief.research_queries or []),
            "format": getattr(brief.format, "value", str(brief.format)),
            "conclusion": brief.conclusion.model_dump(mode="json")
            if brief.conclusion
            else None,
        },
        "research_queries": list(brief.research_queries or []),
        "instruction": (
            "primary_text и story_brief — уже известный материал. "
            "Через googleSearch найди НОВЫЕ факты/материалы по теме. "
            "Не пересказывай статью. Каждый fact с https URL из поиска."
        ),
    }
    if repair_note:
        payload["repair"] = repair_note

    kwargs: dict = {}
    if use_web_search:
        kwargs["tools"] = [GOOGLE_SEARCH_TOOL]
        kwargs["timeout"] = timeout

    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(payload)},
        ],
        **kwargs,
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
    return ResearchPack.model_validate(raw)


def enrich_material(
    dossier: Dossier,
    brief: StoryBrief,
    *,
    llm: ChatModel | None = None,
) -> tuple[Dossier, ResearchPack]:
    """C1.5: статья+бриф как контекст; googleSearch → новые факты с URL."""
    if dossier.frozen:
        raise ValueError("C1.5: dossier уже frozen")

    use_web, timeout = _research_settings()
    model = llm or get_research_enrich_model(temperature=0.2)

    pack = _invoke_pack(
        model=model,
        dossier=dossier,
        brief=brief,
        use_web_search=use_web,
        timeout=timeout,
    )
    # С googleSearch принимаем любые http(s) URL; local:// — только fallback.
    verified = [
        fact
        for fact in pack.facts
        if _is_http_url(fact.source_url)
        or (not use_web and fact.source_url.startswith("local://"))
    ]

    if not verified and (dossier.material_notes or "").strip():
        if hasattr(model, "stage"):
            model.stage = "C1.5 research enricher · repair"
        pack = _invoke_pack(
            model=model,
            dossier=dossier,
            brief=brief,
            use_web_search=use_web,
            timeout=timeout,
            repair_note=(
                "Предыдущий ответ отклонён: нет facts с https:// URL из поиска. "
                "Снова вызови googleSearch. Верни ТОЛЬКО новые материалы, "
                "которых нет в primary_text. Не пересказывай статью."
            ),
        )
        verified = [
            fact
            for fact in pack.facts
            if _is_http_url(fact.source_url)
            or (not use_web and fact.source_url.startswith("local://"))
        ]

    verified_pack = pack.model_copy(update={"facts": verified, "gaps": pack.gaps[:3]})
    if not verified:
        return dossier, verified_pack

    additions = "\n".join(
        f"- {fact.fact} [{fact.source_title or fact.source_url}] — {fact.why_it_matters}"
        for fact in verified
    )
    enriched = dossier.model_copy(
        update={
            "material_notes": (
                f"{dossier.material_notes}\n\nДОПОЛНИТЕЛЬНЫЕ ПРОВЕРЯЕМЫЕ ФАКТЫ (web):\n{additions}"
            )
        }
    )
    return enriched, verified_pack
