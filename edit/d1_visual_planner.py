"""D1.5: визуальный сценарий между frozen dossier и живой речью D2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edit.llm import ChatModel, invoke_json
from edit.model_routing import get_personal_story_model
from edit.search import ImageSearcher, SearchHit, SearchUnavailableError, default_searcher
from models import (
    Dossier,
    StoryBrief,
    VisualPlanBeat,
    VisualReference,
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
    return " ".join(
        (text or "")
        .lower()
        .replace("«", '"')
        .replace("»", '"')
        .replace("—", "-")
        .split()
    )


def _validate_source_quotes(plan: VisualScenarioPlan, source: str) -> None:
    haystack = _normalize_quote(source)
    for beat in plan.beats:
        quote = _normalize_quote(beat.source_quote)
        if quote not in haystack:
            raise ValueError(
                "D1.5: source_quote не найдена в первичном тексте для "
                f"{beat.beat_id}: {beat.source_quote[:120]}"
            )


def plan_visual_scenario(
    dossier: Dossier,
    brief: StoryBrief,
    *,
    primary_text: str = "",
    image_searcher: ImageSearcher | None = None,
    llm: ChatModel | None = None,
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
    _validate_source_quotes(plan, primary_text or dossier.material_notes)
    return _image_refs(plan, searcher=image_searcher)
