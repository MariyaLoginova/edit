"""D1.5: визуальный сценарий между frozen dossier и живой речью D2."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from edit.llm import ChatModel, invoke_json
from edit.model_routing import get_personal_story_model
from edit.search import ImageSearcher, SearchHit, SearchUnavailableError, default_searcher
from models import (
    Dossier,
    StoryBrief,
    VisualPlanBeat,
    VisualReference,
    VisualResearchPack,
    VisualScenarioPlan,
    can_freeze,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d1_visual_planner.txt"


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _image_refs(
    plan: VisualScenarioPlan,
    *,
    searcher: ImageSearcher | None,
    results_per_beat: int = 3,
) -> VisualScenarioPlan:
    """Разрешить image_query через Brave/совместимый image searcher.

    Сбой поиска не отменяет сценарий: продакшен видит статус и может подобрать
    архивные изображения вручную.
    """
    image_searcher = searcher or default_searcher()
    beats: list[VisualPlanBeat] = []
    found = 0
    try:
        for beat in plan.beats:
            hits: list[SearchHit] = image_searcher.search_images(
                beat.image_query, max_results=results_per_beat
            )
            refs = [
                VisualReference(url=hit.url, title=hit.title, description=hit.snippet)
                for hit in hits
                if hit.url
            ]
            found += len(refs)
            beats.append(beat.model_copy(update={"image_references": refs}))
    except (SearchUnavailableError, AttributeError) as exc:
        return plan.model_copy(
            update={
                "image_search_status": "unavailable",
                "image_search_error": str(exc),
            }
        )
    return plan.model_copy(
        update={
            "beats": beats,
            "image_search_status": "ok" if found else "empty",
            "image_search_error": None,
        }
    )


def _normalize_quote(text: str) -> str:
    normalized = (
        (text or "")
        .lower()
        .replace("«", '"')
        .replace("»", '"')
        .replace("—", "-")
        .replace("–", "-")
        .replace("\u00a0", " ")
        .replace("ё", "е")
    )
    # OCR часто рвёт абзац колонтитулом «134 Все оттенки…»
    normalized = re.sub(
        r"\d{1,3}\s+все оттенки черного[^\n]*",
        " ",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r"[^\w\s-]+", " ", normalized, flags=re.UNICODE)
    return re.sub(r"\s+", " ", normalized).strip()


def _quote_in_haystack(quote: str, haystack: str) -> bool:
    if not quote:
        return False
    if quote in haystack:
        return True
    # Длинная цитата: достаточно ядра ≥40 символов (OCR-разрывы).
    if len(quote) >= 48:
        core = quote[4:-4] if len(quote) > 56 else quote
        if len(core) >= 40 and core in haystack:
            return True
    return False


def _validate_source_quotes(
    plan: VisualScenarioPlan,
    source: str,
    research: VisualResearchPack | None = None,
) -> None:
    haystack = _normalize_quote(source)
    for beat in plan.beats:
        quote = _normalize_quote(beat.source_quote)
        if _quote_in_haystack(quote, haystack):
            continue
        external_text = ""
        if research is not None and beat.source_url:
            for finding in research.findings:
                for ref in finding.web_references:
                    if ref.url == beat.source_url:
                        external_text += f" {ref.title} {ref.description}"
        if not _quote_in_haystack(quote, _normalize_quote(external_text)):
            raise ValueError(
                "D1.5: source_quote не найдена в первичном тексте для "
                f"{beat.beat_id}: {beat.source_quote[:120]}"
            )


def plan_visual_scenario(
    dossier: Dossier,
    brief: StoryBrief,
    *,
    primary_text: str = "",
    visual_research: VisualResearchPack | None = None,
    image_searcher: ImageSearcher | None = None,
    llm: ChatModel | None = None,
    _repair_attempt: int = 0,
    _repair_note: str = "",
) -> VisualScenarioPlan:
    """Собрать план 3–5 минут: что показывать, когда и по какому запросу искать."""
    if not dossier.frozen:
        raise ValueError("D1.5: нужен frozen dossier")
    ok, problems = can_freeze(dossier, require_images=False)
    if not ok:
        raise ValueError("D1.5: неполное досье — " + "; ".join(problems))
    model = llm or get_personal_story_model(temperature=0.2)
    user: dict[str, Any] = {
        "duration_range_sec": {"min": 180, "max": 300},
        "story_brief_for_speech": brief.for_d2(),
        "source_material": _clip(primary_text or dossier.material_notes, 18000),
        "dossier_material": {
            "object_anchor": dossier.claim.object_anchor,
            "visual_hint": dossier.claim.visual_hint,
            "material_notes": _clip(dossier.material_notes, 9000),
            "web_confirmations": [
                c.model_dump(mode="json")
                for c in dossier.web_confirmations
                if c.supports_claim
            ],
        },
        "external_visual_research": (
            visual_research.model_dump(mode="json") if visual_research else None
        ),
        "validation_repair": _repair_note,
    }
    raw = invoke_json(
        model,
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ],
        retries=1,
    )
    if not isinstance(raw, dict):
        raise ValueError("D1.5: ожидался JSON VisualScenarioPlan")
    raw.setdefault("claim_id", dossier.claim_id)
    raw.setdefault("format", brief.format.value)
    plan = VisualScenarioPlan.model_validate(raw)
    if plan.claim_id != dossier.claim_id:
        raise ValueError("D1.5: claim_id сценария не совпадает с досье")
    if plan.format != brief.format:
        raise ValueError("D1.5: format сценария не совпадает с StoryBrief")
    try:
        _validate_source_quotes(plan, primary_text or dossier.material_notes, visual_research)
    except ValueError as exc:
        if _repair_attempt >= 1:
            raise
        # Один repair-вызов при битой цитате (часто OCR/колонтитул).
        # В трейсе AuditedLLM помечаем стадию, чтобы не выглядело как «дубль».
        if hasattr(model, "stage"):
            model.stage = "D1.5 visual plan · repair"
        return plan_visual_scenario(
            dossier,
            brief,
            primary_text=primary_text,
            visual_research=visual_research,
            image_searcher=image_searcher,
            llm=model,
            _repair_attempt=1,
            _repair_note=(
                f"Предыдущий план отклонён: {exc}. Верни весь VisualScenarioPlan "
                "заново. source_quote каждого бита должна быть дословной "
                "непрерывной цитатой из source_material; не сокращай и не "
                "перефразируй её. Не вставляй колонтитулы OCR в середину цитаты."
            ),
        )
    return _image_refs(plan, searcher=image_searcher)
