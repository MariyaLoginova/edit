"""E-редактор до сценария: форма, хук и причина переслать (FIX-5)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from edit.audience import load_audience
from edit.config import ROOT
from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_personal_story_model
from edit.library import (
    NONE_ID,
    compose_system_prompt,
    idea_trigger_menu,
    load_idea_triggers,
    normalize_library_id,
)
from edit.structures import normalize_structure_id, structure_menu
from models import ClaimCard, EndingType, StoryBrief

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e_editor.txt"
METHODS_PATH = ROOT / "config" / "story_methods.yaml"
HOOKS_PATH = ROOT / "config" / "hook_triggers.yaml"
_CHRONOLOGY_ANGLE = re.compile(
    r"(?i)^(хронолог|линейн\w*\s*пересказ|по\s*порядк|timeline|"
    r"сначала.{0,40}потом.{0,40}потом|1960\s*[→\->])"
)
_QUOTE_CHARS = str.maketrans(
    {
        "«": '"',
        "»": '"',
        "“": '"',
        "”": '"',
        "„": '"',
        "‚": "'",
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "\u00a0": " ",
    }
)


def _normalize_quote_text(text: str) -> str:
    cleaned = text.translate(_QUOTE_CHARS)
    cleaned = cleaned.lower()
    # Пунктуация на границах слов не должна валить дословную опору.
    cleaned = re.sub(r"[^\w\s\-]+", " ", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _locate_source_quote(quote: str, primary_text: str) -> str | None:
    """Находит дословную опору с допуском на кавычки/пробелы; возвращает фрагмент из источника."""
    if not quote:
        return None
    if quote in primary_text:
        return quote
    needle = _normalize_quote_text(quote)
    if not needle:
        return None
    # Скользящее окно по словам источника: ищем совпадение нормализованной строки.
    words = re.findall(r"\S+", primary_text)
    needle_words = needle.split()
    if not needle_words or len(needle_words) > len(words):
        return None
    for start in range(0, len(words) - len(needle_words) + 1):
        window = words[start : start + len(needle_words)]
        if _normalize_quote_text(" ".join(window)) == needle:
            # Вернуть фрагмент источника без хвостовой пунктуации последнего слова,
            # если цитата её не содержала.
            joined = " ".join(window)
            if not re.search(r"[.!?…]$", quote.strip()) and joined[-1:] in ".!?…":
                joined = joined[:-1]
            return joined
    return None


def load_story_methods() -> list[dict]:
    return yaml.safe_load(METHODS_PATH.read_text(encoding="utf-8")) or []


def load_hook_triggers() -> list[dict]:
    return yaml.safe_load(HOOKS_PATH.read_text(encoding="utf-8")) or []


def plan_story(
    claim: ClaimCard,
    *,
    primary_text: str = "",
    llm: ChatModel | None = None,
    _repair_attempt: int = 0,
    _repair_note: str = "",
) -> StoryBrief:
    model = llm or get_personal_story_model(temperature=0.2)
    response = model.invoke(
        [
            {
                "role": "system",
                "content": compose_system_prompt(PROMPT_PATH, "e_editor_menu"),
            },
            {
                "role": "user",
                "content": str(
                    {
                        "claim": claim.model_dump(mode="json"),
                        "primary_text": primary_text,
                        "audience": load_audience(),
                        "menu_story_methods": load_story_methods(),
                        "menu_reel_structures": structure_menu(),
                        "menu_idea_triggers": idea_trigger_menu(),
                        "hook_triggers": load_hook_triggers(),
                        "contract_repair": _repair_note,
                    }
                ),
            },
        ]
    )
    raw = parse_json_payload(content_text(response))
    if not isinstance(raw, dict):
        raise ValueError("E-редактор: ожидался JSON-объект")
    if "recommended_method" not in raw:
        for wrapper in ("StoryBrief", "story_brief"):
            if isinstance(raw.get(wrapper), dict):
                raw = raw[wrapper]
                break
    aliases = {
        "key_idea": "main_thought",
        "main_idea": "main_thought",
        "primary_method": "recommended_method",
        "method": "recommended_method",
        "selected_story_method": "recommended_method",
        "selected_method": "recommended_method",
        "main_story_method": "recommended_method",
        "hook": "opening",
        "hook_text": "opening",
        "fantogramma": "angle",
        "fantogram_angle": "angle",
        "story_angle": "angle",
        "viewer_hook": "why_viewer",
        "why_it_matters": "why_viewer",
        "why_audience": "why_viewer",
        "why_audience_cares": "why_viewer",
        "why_share": "share_reason",
        "impress_colleagues": "share_reason",
        "methods": "alternative_methods",
        "alternative_story_methods": "alternative_methods",
        "personal_pitch": "idea_pitch",
        "pitch": "idea_pitch",
        "idea": "idea_pitch",
        "idea_probe": "idea_pitch",
        "structure": "selected_structure",
        "structure_id": "selected_structure",
        "reel_structure": "selected_structure",
        "idea_trigger": "selected_idea_trigger",
        "idea_angle": "selected_idea_trigger",
    }
    for source, target in aliases.items():
        if target not in raw and source in raw:
            raw[target] = raw[source]
    raw.setdefault("main_thought", raw.get("claim") or claim.claim)
    if isinstance(raw.get("main_thought"), str):
        raw["main_thought"] = raw["main_thought"][:400]
    if isinstance(raw.get("angle"), dict):
        ang = raw["angle"]
        raw["angle"] = (
            ang.get("text")
            or ang.get("move")
            or ang.get("name")
            or " ".join(str(x) for x in ang.values() if x)
        )
    if not raw.get("angle"):
        raw["angle"] = (
            raw.get("fantogramma_move")
            or raw.get("angle_move")
            or "сделать наоборот — привычное чтение ломается деталью"
        )
    if isinstance(raw.get("angle"), str):
        raw["angle"] = raw["angle"][:280]
    if isinstance(raw.get("why_viewer"), dict):
        wv = raw["why_viewer"]
        raw["why_viewer"] = wv.get("text") or wv.get("reason") or wv.get("why") or ""
    if not raw.get("why_viewer"):
        raw["why_viewer"] = (
            raw.get("audience_reason")
            or raw.get("why_watch")
            or "Это про то, как ты читаешь знакомый визуал в своей работе."
        )
    if isinstance(raw.get("why_viewer"), str):
        raw["why_viewer"] = raw["why_viewer"][:300]
    # audience_reason — наследник why_viewer для старых потребителей брифа.
    if not raw.get("audience_reason"):
        raw["audience_reason"] = raw["why_viewer"]
    evidence = raw.get("visual_evidence")
    if isinstance(evidence, list):
        raw["visual_evidence"] = "; ".join(str(x).strip() for x in evidence if str(x).strip())
    elif isinstance(evidence, dict):
        raw["visual_evidence"] = (
            evidence.get("text")
            or evidence.get("frames")
            or evidence.get("description")
            or ""
        )
        if isinstance(raw["visual_evidence"], list):
            raw["visual_evidence"] = "; ".join(
                str(x).strip() for x in raw["visual_evidence"] if str(x).strip()
            )
    if isinstance(raw.get("visual_evidence"), str):
        raw["visual_evidence"] = raw["visual_evidence"][:200]
    method = (
        raw.get("story_method")
        or raw.get("story_type")
        or raw.get("selected_story_method")
    )
    if not raw.get("recommended_method") and isinstance(method, dict):
        raw["recommended_method"] = (
            method.get("id")
            or method.get("primary_method")
            or method.get("primary")
            or method.get("method")
            or method.get("name")
        )
    if "alternative_methods" not in raw and isinstance(method, dict):
        raw["alternative_methods"] = method.get("alternatives") or []
    if isinstance(raw.get("recommended_method"), dict):
        raw["recommended_method"] = (
            raw["recommended_method"].get("id")
            or raw["recommended_method"].get("primary")
            or raw["recommended_method"].get("name")
            or ""
        )
    if "opening" not in raw and "hook" in raw:
        raw["opening"] = raw["hook"]
    opening = raw.get("opening")
    if isinstance(opening, dict):
        trigger = opening.get("trigger")
        raw["hook_trigger"] = raw.get("hook_trigger") or (
            trigger.get("id") if isinstance(trigger, dict) else trigger
        )
        raw["opening"] = (
            opening.get("text")
            or opening.get("hook")
            or opening.get("headline")
            or (trigger.get("text") if isinstance(trigger, dict) else None)
            or ""
        )
    if not raw.get("opening"):
        raw["opening"] = (
            raw.get("opening_text")
            or raw.get("opening_line")
            or raw.get("hook_line")
            or claim.counter_expectation
        )
    if isinstance(raw.get("opening"), str):
        raw["opening"] = raw["opening"][:280]
    if isinstance(raw.get("hook_trigger"), dict):
        hook = raw["hook_trigger"]
        if not raw.get("opening"):
            raw["opening"] = hook.get("hook_text") or hook.get("text") or ""
        raw["hook_trigger"] = hook.get("id") or hook.get("name") or ""
    if isinstance(opening, dict) and not raw.get("hook_trigger"):
        raw["hook_trigger"] = opening.get("trigger_id") or ""
    audience = raw.get("audience")
    audience = audience or raw.get("audience_retention_and_payoff")
    if "audience_reason" not in raw and isinstance(audience, dict):
        raw["audience_reason"] = (
            audience.get("reason") or audience.get("why") or audience.get("fit") or ""
        )
    if "share_reason" not in raw and isinstance(audience, dict):
        raw["share_reason"] = audience.get("share_reason") or audience.get("status") or ""
    if not raw.get("audience_reason"):
        raw["audience_reason"] = (
            raw.get("why_viewer")
            or raw.get("why_watch")
            or raw.get("why_watch_till_end")
            or (audience.get("why_watch_till_end") if isinstance(audience, dict) else None)
            or raw.get("audience_fit")
            or "Даёт исторический контекст знакомому визуальному маркеру."
        )
    if not raw.get("share_reason"):
        raw["share_reason"] = (
            raw.get("status_gain")
            or raw.get("status_flex")
            or raw.get("flex_for_colleague")
            or (audience.get("flex_value") if isinstance(audience, dict) else None)
            or raw.get("share_value")
            or "Есть острый угол и конкретный образ, чтобы спорить с коллегами."
        )
    for key in ("audience_reason", "share_reason"):
        if isinstance(raw.get(key), dict):
            raw[key] = raw[key].get("text") or raw[key].get("reason") or ""
    for key in ("audience_reason", "share_reason"):
        if isinstance(raw.get(key), str):
            raw[key] = raw[key][:300]
    proof_plan = raw.get("proof_plan")
    if isinstance(proof_plan, list):
        raw["proof_plan"] = [
            {
                "point": item.get("point") or item.get("detail") or item.get("text") or item.get("fact") or "",
                "source_quote": (
                    item.get("source_quote")
                    or item.get("quote")
                    or item.get("citation")
                    or ""
                ),
            }
            if isinstance(item, dict)
            else {"point": str(item), "source_quote": ""}
            for item in proof_plan
        ]
    if isinstance(raw.get("idea_pitch"), dict):
        pitch = raw["idea_pitch"]
        raw["idea_pitch"] = (
            pitch.get("text")
            or pitch.get("pitch")
            or pitch.get("idea")
            or pitch.get("voiced_marker")
            or ""
        )
    if isinstance(raw.get("idea_pitch"), str):
        raw["idea_pitch"] = raw["idea_pitch"][:280]
    if not raw.get("idea_pitch"):
        raw["idea_pitch"] = (
            "А если вернуть этот образ туда, откуда он родом — во взрослый регистр?"
        )
    if not raw.get("needs_external_research"):
        raw["research_queries"] = []
    elif not raw.get("research_queries"):
        raw["research_queries"] = (
            raw.get("queries")
            or raw.get("search_queries")
            or [
                " ".join(
                    x for x in (claim.scope.author_or_work, claim.scope.period, claim.object_anchor) if x
                )
            ]
        )
    alternatives = raw.get("alternative_methods")
    if isinstance(alternatives, list):
        raw["alternative_methods"] = [
            item.get("id") or item.get("name") or "" if isinstance(item, dict) else item
            for item in alternatives
        ]
    raw.setdefault("claim_id", claim.claim_id)
    raw.setdefault("ending_type", EndingType.formula.value)
    raw["selected_structure"] = normalize_structure_id(
        raw.get("selected_structure")
    )
    raw["selected_idea_trigger"] = normalize_library_id(
        raw.get("selected_idea_trigger"),
        known_ids={item["id"] for item in load_idea_triggers()} | {NONE_ID},
    )
    try:
        brief = StoryBrief.model_validate(raw)
        _validate_visual_contract(brief, primary_text)
        return brief
    except Exception as exc:
        if _repair_attempt >= 1:
            raise ValueError(f"E-редактор не выполнил контракт после retry: {exc}") from exc
        return plan_story(
            claim,
            primary_text=primary_text,
            llm=model,
            _repair_attempt=1,
            _repair_note=(
                f"Предыдущий ответ отклонён валидатором: {exc}. Верни заново валидный "
                "StoryBrief: angle (не хронология), why_viewer (связь со зрителем), "
                "visual_evidence, ровно 3 proof_plan с дословными source_quote — "
                "каждая quote должна буквально встречаться в primary_text."
            ),
        )


def _validate_visual_contract(brief: StoryBrief, primary_text: str) -> None:
    """Кодовая приёмка: angle/why_viewer и три дословные опоры."""
    if not brief.angle.strip():
        raise ValueError("нужен angle — ход, ломающий линейность")
    if _CHRONOLOGY_ANGLE.search(brief.angle.strip()):
        raise ValueError(
            "angle не должен быть хронологией; возьми ход фантограммы"
        )
    if not brief.why_viewer.strip():
        raise ValueError("нужен why_viewer — связь со зрителем")
    if not primary_text:
        raise ValueError("нужен primary_text для проверки proof_plan")
    missing: list[str] = []
    for item in brief.proof_plan:
        located = _locate_source_quote(item.source_quote, primary_text)
        if located is None:
            missing.append(item.source_quote)
        else:
            item.source_quote = located[:700]
    if missing:
        raise ValueError("source_quote не найдена в первичном тексте: " + missing[0][:120])
