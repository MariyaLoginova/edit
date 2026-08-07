"""D2 FIX-5: личный plain-text монолог вместо JSON-сценария."""

from __future__ import annotations

import re
from pathlib import Path

from edit.audience import load_audience
from edit.config import ROOT
from edit.llm import ChatModel, content_text
from edit.model_routing import PolicyBlockedError, get_personal_story_model, is_policy_text
from edit.library import get_idea_trigger
from edit.structures import get_structure
from models import Dossier, MonologueDraft, StoryBrief, can_freeze

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d2_monologue.txt"
METHODS_PATH = ROOT / "config" / "story_methods.yaml"
_WRITING_ENVELOPE = re.compile(
    r"^:::writing[^\n]*\n?|^:::\s*$", re.MULTILINE | re.IGNORECASE
)
_MONOLOGUE_LABEL = re.compile(r"(?im)^\s*готовый\s+монолог\s*:\s*")
_BANNED_OPENERS = (
    "а вот нифига",
    "все думают",
    "на самом деле",
    "секрет, который",
)
_BANNED_EMPTY = (
    "кража-с-переносом",
    "меняешь контекст — меняешь смысл",
    "меняешь контекст - меняешь смысл",
    "не фантазия скульптора",
    "а дальше фокус похлеще",
    "и вот тут уже смешно",
    "смотри внимательно",
    "а теперь главное",
    "заметь фокус",
    "и тут поворот",
    "вот тебе",
)


def _word_bounds() -> tuple[int, int]:
    return 200, 300


def _methods() -> list[dict]:
    import yaml

    return yaml.safe_load(METHODS_PATH.read_text(encoding="utf-8")) or []


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
    lo, hi = _word_bounds()
    model = llm or get_personal_story_model(temperature=0.3)
    # Полная глава в payload ломает провайдеров («message too long») и жрёт деньги.
    notes = (dossier.material_notes or "").strip()
    if len(notes) > 4500:
        notes = notes[:4500].rstrip() + "…"
    web_slim = []
    for c in dossier.web_confirmations:
        if not c.supports_claim:
            continue
        item = c.model_dump(mode="json")
        snip = str(item.get("snippet") or "")
        if len(snip) > 500:
            item["snippet"] = snip[:500].rstrip() + "…"
        web_slim.append(item)
    user = {
        "dossier": {
            # Claim — якорь темы, не текст для копирования.
            "theme_anchor": {
                "claim_id": dossier.claim_id,
                "object_anchor": dossier.claim.object_anchor,
                "contrast_pair": dossier.claim.contrast_pair.model_dump(mode="json"),
            },
            "material_notes": notes,
            "web_confirmations": web_slim,
        },
        "audience": load_audience(),
        "story_brief": {
            **{
                k: v
                for k, v in brief.model_dump(mode="json").items()
                if k not in {"idea_pitch", "share_reason"}
            },
            # Слоганы из брифа тянут пустой финал — D2 их не ест.
            "ending_type": "reactive",
        },
        "must_include": {
            "proof_plan": [item.model_dump(mode="json") for item in brief.proof_plan],
            "hook_draft": hook_text or brief.opening,
            "structure": [
                "start with the given hook_draft first_line verbatim",
                "immediately name the objects/prototype — no filler warmup",
                "follow reel_structure beats/full_example if provided",
                "aggressive sarcastic story through three visual proofs",
                "more meat/scenes, zero empty intensifiers",
                "viewer questions at the end; no opaque slogan",
            ],
            "never_in_speech": [
                "автор книги",
                "название книги",
                "читаю у…",
                "по данным исследования",
                "а вот нифига",
                "все думают",
                "кража-с-переносом",
                "меняешь контекст — меняешь смысл",
                "не фантазия скульптора",
                "а дальше фокус похлеще",
                "и вот тут уже смешно",
                "смотри внимательно",
                "а теперь главное",
            ],
        },
        "story_method": next(
            (m for m in _methods() if m.get("id") == brief.recommended_method), None
        ),
        "word_limit": {"min": lo, "max": hi},
    }
    selected = get_structure(brief.selected_structure)
    if selected is not None:
        user["reel_structure"] = {
            "id": selected["id"],
            "name": selected.get("name"),
            "beats": selected.get("beats") or [],
            "full_example": selected.get("full_example") or "",
            "adapt_note": (
                "Используй ритм и биты примера. CTA/продажу из примера "
                "замени вопросом зрителю, если канал не про оффер."
            ),
        }
    else:
        user["reel_structure"] = None
    idea = get_idea_trigger(brief.selected_idea_trigger)
    user["idea_trigger"] = (
        {
            "id": idea["id"],
            "name": idea.get("name"),
            "angle": idea.get("angle") or "",
        }
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
                    f"вышло {words} слов — коротко; допиши мясо/сцены "
                    f"до {lo}–{hi} (ещё конкретные детали, не вводные)"
                )
            elif words > hi:
                problems.append(
                    f"вышло {words} слов — обрежь до {lo}–{hi}, не трогая хук и три улики"
                )
            if any(
                filler in text.lower()
                for filler in (
                    "фокус похлеще",
                    "вот тут уже смешно",
                    "смотри внимательно",
                    "а теперь главное",
                )
            ):
                problems.append(
                    "убери пустые вводные; после хука сразу к предмету и фактам"
                )
            lowered = text.lower()
            banned = [
                phrase
                for phrase in (*_BANNED_OPENERS, *_BANNED_EMPTY)
                if phrase in lowered
            ]
            if banned:
                problems.append("убери стоп-фразы: " + ", ".join(banned))
            if "?" not in text:
                problems.append("в финале нужен вопрос зрителю для обсуждения")
            if selected_hook and not text.startswith(selected_hook):
                problems.append(f"начни ровно с хука: {selected_hook}")
            repair = "Перепиши целиком. " + " ".join(problems)
        response = content_text(
            model.invoke(
                [
                    {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
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
        if re.search(r"(?i)message you submitted was too long|context length|maximum context", text):
            text = ""
            words = 0
            continue
        if selected_hook and not text.startswith(selected_hook):
            # Жёстко подставляем выбранный хук, если модель снова ушла в свой зачин.
            rest = text
            for phrase in _BANNED_OPENERS:
                rest = re.sub(rf"(?is)^.*?{re.escape(phrase)}[:!]?\s*", "", rest, count=1)
            text = f"{selected_hook} {rest}".strip()
        words = len(re.findall(r"\S+", text))
        banned_hit = any(
            phrase in text.lower() for phrase in (*_BANNED_OPENERS, *_BANNED_EMPTY)
        )
        if (
            lo <= words <= hi
            and not banned_hit
            and "?" in text
            and (not selected_hook or text.startswith(selected_hook))
        ):
            break
    if not lo <= words <= hi:
        raise ValueError(f"D2: вышло {words} слов после retry; нужно {lo}–{hi}")
    if any(phrase in text.lower() for phrase in (*_BANNED_OPENERS, *_BANNED_EMPTY)):
        raise ValueError("D2: стоп-фраза осталась после retry")
    if "?" not in text:
        raise ValueError("D2: нет вопроса зрителю после retry")
    return MonologueDraft(
        claim_id=dossier.claim_id,
        text=text,
        word_count=words,
        story_method=brief.recommended_method,
        ending_type="reactive",
    )
