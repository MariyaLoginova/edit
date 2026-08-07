"""D2: монолог по EDIT-FORM — экскурсия (по умолчанию) или аргумент."""

from __future__ import annotations

import re
from pathlib import Path

from edit.config import ROOT
from edit.library import banned_speech_phrases, compose_system_prompt, get_idea_trigger
from edit.llm import ChatModel, content_text
from edit.model_routing import PolicyBlockedError, get_personal_story_model, is_policy_text
from edit.structures import get_structure
from models import Dossier, MonologueDraft, ReelFormat, StoryBrief, can_freeze

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d2_monologue.txt"
METHODS_PATH = ROOT / "config" / "story_methods.yaml"
_WRITING_ENVELOPE = re.compile(
    r"^:::writing[^\n]*\n?|^:::\s*$", re.MULTILINE | re.IGNORECASE
)
_MONOLOGUE_LABEL = re.compile(r"(?im)^\s*готовый\s+монолог\s*:\s*")


def _word_bounds(fmt: ReelFormat) -> tuple[int, int]:
    if fmt == ReelFormat.excursion:
        return 160, 280
    return 200, 300


def _methods() -> list[dict]:
    import yaml

    return yaml.safe_load(METHODS_PATH.read_text(encoding="utf-8")) or []


def _find_banned(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in banned_speech_phrases() if phrase in lowered]


def _source_notes(dossier: Dossier, brief: StoryBrief) -> str:
    notes_full = (dossier.material_notes or "").strip()
    windows: list[str] = []
    used = 0
    for quote in brief.source_anchors():
        q = (quote or "").strip()
        if not q or not notes_full:
            continue
        idx = notes_full.find(q)
        if idx < 0:
            continue
        start = max(0, idx - 120)
        end = min(len(notes_full), idx + len(q) + 120)
        piece = notes_full[start:end].strip()
        if piece in windows:
            continue
        if used + len(piece) > 1800:
            break
        windows.append(piece)
        used += len(piece)
    head_budget = max(1200, 4500 - used)
    notes = notes_full[:head_budget].rstrip()
    if len(notes_full) > head_budget:
        notes += "…"
    if windows:
        notes = notes + "\n\n--- source windows ---\n\n" + "\n\n---\n\n".join(windows)
    return notes


def write_monologue(
    dossier: Dossier,
    brief: StoryBrief,
    *,
    hook_text: str | None = None,
    llm: ChatModel | None = None,
) -> MonologueDraft:
    if not dossier.frozen:
        raise ValueError("D2: нужен frozen dossier")
    ok, problems = can_freeze(dossier, require_images=False)
    if not ok:
        raise ValueError("D2: неполное досье — " + "; ".join(problems))
    if not brief.topic_ready:
        raise ValueError("D2: тема не готова — нет вывода из источника")
    lo, hi = _word_bounds(brief.format)
    model = llm or get_personal_story_model(temperature=0.3)
    notes = _source_notes(dossier, brief)
    web_slim = []
    for c in dossier.web_confirmations:
        if not c.supports_claim:
            continue
        item = c.model_dump(mode="json")
        snip = str(item.get("snippet") or "")
        if len(snip) > 500:
            item["snippet"] = snip[:500].rstrip() + "…"
        web_slim.append(item)

    speakable = brief.for_d2()
    # Жёсткая страховка: служебные ключи не должны утечь.
    for forbidden in (
        "why_viewer",
        "audience_reason",
        "share_reason",
        "idea_pitch",
        "recommended_method",
        "alternative_methods",
        "audience",
    ):
        speakable.pop(forbidden, None)

    user: dict = {
        "dossier": {
            "theme_anchor": {
                "claim_id": dossier.claim_id,
                "object_anchor": dossier.claim.object_anchor,
                "contrast_pair": dossier.claim.contrast_pair.model_dump(mode="json"),
            },
            "material_notes": notes,
            "web_confirmations": web_slim,
        },
        # Только озвучиваемый слой — без why_viewer / audience / idea_pitch.
        "story_brief": speakable,
        "must_include": {
            "hook_draft": hook_text or brief.opening,
            "conclusion_plain": brief.conclusion.plain,
            "structure": (
                [
                    "start with hook_draft verbatim",
                    "walk exhibits: 1–2 short phrases each, observation only",
                    "no mid-roll meaning explanations",
                    "say conclusion_plain once at the end, lightly",
                    "final line: simple question about what was shown",
                ]
                if brief.format == ReelFormat.excursion
                else [
                    "start with hook_draft verbatim",
                    "one thesis + exactly three proof_plan beats",
                    "conclusion_plain once at the end",
                    "final line: simple question about what was shown",
                ]
            ),
            "never_in_speech": banned_speech_phrases()
            + [
                "автор книги",
                "название книги",
                "читаю у…",
                "по данным исследования",
            ],
        },
        "word_limit": {"min": lo, "max": hi},
    }
    # Метод и структура — ритм для argument; для экскурсии не тащим чужой оффер.
    if brief.format == ReelFormat.argument:
        user["story_method"] = next(
            (m for m in _methods() if m.get("id") == brief.recommended_method), None
        )
        selected = get_structure(brief.selected_structure)
        if selected is not None:
            user["reel_structure"] = {
                "id": selected["id"],
                "name": selected.get("name"),
                "beats": selected.get("beats") or [],
                "full_example": selected.get("full_example") or "",
                "adapt_note": (
                    "Ритм примера ок. CTA/продажу замени простым вопросом "
                    "про показанное."
                ),
            }
        else:
            user["reel_structure"] = None
        idea = get_idea_trigger(brief.selected_idea_trigger)
        user["idea_trigger"] = (
            {"id": idea["id"], "name": idea.get("name"), "angle": idea.get("angle") or ""}
            if idea is not None
            else None
        )

    selected_hook = (hook_text or "").strip()
    text = ""
    words = 0
    for attempt in range(5):
        repair = ""
        if attempt > 0:
            problems = []
            if words < lo:
                problems.append(
                    f"вышло {words} слов — коротко; допиши наблюдения "
                    f"до {lo}–{hi} (ещё экспонаты/детали, не нравоучения)"
                )
            elif words > hi:
                problems.append(
                    f"вышло {words} слов — обрежь до {lo}–{hi}, не трогая хук и вывод"
                )
            banned = _find_banned(text)
            if banned:
                problems.append(
                    "убери служебные/запрещённые обороты: " + ", ".join(banned)
                )
            if "?" not in text:
                problems.append(
                    "в финале нужен простой вопрос про показанное "
                    "(не про работу зрителя)"
                )
            if selected_hook and not text.startswith(selected_hook):
                problems.append(f"начни ровно с хука: {selected_hook}")
            if re.search(r"(?i)вот почему я теперь|задумайтесь", text):
                problems.append("убери нравоучительный финал; вывод — легко, один раз")
            repair = "Перепиши целиком. " + " ".join(problems)
        response = content_text(
            model.invoke(
                [
                    {
                        "role": "system",
                        "content": compose_system_prompt(
                            PROMPT_PATH, "d2_methods_menu"
                        ),
                    },
                    {
                        "role": "user",
                        "content": str(
                            user if not repair else {**user, "length_repair": repair}
                        ),
                    },
                ]
            )
        ).strip()
        if is_policy_text(response):
            raise PolicyBlockedError(response)
        text = re.sub(r"^```.*?\n|\n```$", "", response, flags=re.S).strip()
        text = _MONOLOGUE_LABEL.sub("", text).strip()
        text = _WRITING_ENVELOPE.sub("", text).strip()
        text = re.sub(r"\bформула\s+простая\s*:\s*", "", text, flags=re.I)
        if re.search(
            r"(?i)message you submitted was too long|context length|maximum context",
            text,
        ):
            text = ""
            words = 0
            continue
        if selected_hook and not text.startswith(selected_hook):
            text = f"{selected_hook} {text}".strip()
        words = len(re.findall(r"\S+", text))
        banned_hit = bool(_find_banned(text))
        if (
            lo <= words <= hi
            and not banned_hit
            and "?" in text
            and (not selected_hook or text.startswith(selected_hook))
        ):
            break
    if not lo <= words <= hi:
        raise ValueError(f"D2: вышло {words} слов после retry; нужно {lo}–{hi}")
    banned_left = _find_banned(text)
    if banned_left:
        raise ValueError(
            "D2: служебные/запрещённые обороты после retry: "
            + ", ".join(banned_left)
        )
    if "?" not in text:
        raise ValueError("D2: нет вопроса зрителю после retry")
    return MonologueDraft(
        claim_id=dossier.claim_id,
        text=text,
        word_count=words,
        story_method=brief.recommended_method,
        ending_type="reactive",
        format=brief.format,
    )
