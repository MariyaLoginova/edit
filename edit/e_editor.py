"""E-редактор до сценария: форма, хук и причина переслать (FIX-5)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from edit.audience import load_audience
from edit.config import ROOT
from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_personal_story_model
from models import ClaimCard, EndingType, StoryBrief

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e_editor.txt"
METHODS_PATH = ROOT / "config" / "story_methods.yaml"
HOOKS_PATH = ROOT / "config" / "hook_triggers.yaml"
_ABSTRACT_THESIS = re.compile(
    r"(?i)\b(репутацион\w*|pr[- ]?щит|маркетингов\w*|бизнес[- ]?логик\w*|"
    r"корпоративн\w*|прибыл\w*)\b"
)
_VISUAL_WORD = re.compile(r"[а-яё]{4,}", re.I)


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
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {
                "role": "user",
                "content": str(
                    {
                        "claim": claim.model_dump(mode="json"),
                        "primary_text": primary_text,
                        "audience": load_audience(),
                        "menu_story_methods": load_story_methods(),
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
        "why_audience": "audience_reason",
        "why_audience_cares": "audience_reason",
        "why_share": "share_reason",
        "impress_colleagues": "share_reason",
        "methods": "alternative_methods",
        "alternative_story_methods": "alternative_methods",
        "personal_pitch": "idea_pitch",
        "pitch": "idea_pitch",
        "idea": "idea_pitch",
        "idea_probe": "idea_pitch",
    }
    for source, target in aliases.items():
        if target not in raw and source in raw:
            raw[target] = raw[source]
    raw.setdefault("main_thought", raw.get("claim") or claim.claim)
    if isinstance(raw.get("main_thought"), str):
        raw["main_thought"] = raw["main_thought"][:400]
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
            raw.get("why_watch")
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
            or "Даёт точный референс и термин для обсуждения с коллегами."
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
                "StoryBrief: visual_evidence, ровно 3 proof_plan с дословными "
                "source_quote, каждая quote должна буквально встречаться в primary_text."
            ),
        )


def _validate_visual_contract(brief: StoryBrief, primary_text: str) -> None:
    """Кодовая приёмка: показываемый тезис и три дословные опоры."""
    if _ABSTRACT_THESIS.search(brief.main_thought):
        raise ValueError(
            "main_thought мотивный/корпоративный; нужен показываемый визуальный тезис"
        )
    if not primary_text:
        raise ValueError("нужен primary_text для проверки proof_plan")
    missing = [
        item.source_quote
        for item in brief.proof_plan
        if item.source_quote not in primary_text
    ]
    if missing:
        raise ValueError("source_quote не найдена в первичном тексте: " + missing[0][:120])
    source_words = set(_VISUAL_WORD.findall(primary_text.lower()))
    evidence_words = set(_VISUAL_WORD.findall(brief.visual_evidence.lower()))
    if len(source_words & evidence_words) < 2:
        raise ValueError(
            "visual_evidence не называет конкретные предметы/кадры из первичного текста"
        )
