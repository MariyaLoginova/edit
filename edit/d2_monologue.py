"""D2 FIX-5: личный plain-text монолог вместо JSON-сценария."""

from __future__ import annotations

import re
from pathlib import Path

from edit.audience import load_audience
from edit.config import ROOT
from edit.llm import ChatModel, content_text
from edit.model_routing import PolicyBlockedError, get_personal_story_model, is_policy_text
from models import Dossier, MonologueDraft, StoryBrief, can_freeze

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d2_monologue.txt"
METHODS_PATH = ROOT / "config" / "story_methods.yaml"
_WRITING_ENVELOPE = re.compile(
    r"^:::writing[^\n]*\n?|^:::\s*$", re.MULTILINE | re.IGNORECASE
)
_MONOLOGUE_LABEL = re.compile(r"(?im)^\s*готовый\s+монолог\s*:\s*")


def _word_bounds() -> tuple[int, int]:
    return 105, 115


def _methods() -> list[dict]:
    import yaml

    return yaml.safe_load(METHODS_PATH.read_text(encoding="utf-8")) or []


def write_monologue(
    dossier: Dossier,
    brief: StoryBrief,
    *,
    llm: ChatModel | None = None,
) -> MonologueDraft:
    if not dossier.frozen:
        raise ValueError("D2: нужен frozen dossier")
    ok, problems = can_freeze(dossier, require_images=False)
    if not ok:
        raise ValueError("D2: неполное досье — " + "; ".join(problems))
    lo, hi = _word_bounds()
    model = llm or get_personal_story_model(temperature=0.3)
    user = {
        "dossier": {
            # Claim — якорь темы, не текст для копирования.
            "theme_anchor": {
                "claim_id": dossier.claim_id,
                "object_anchor": dossier.claim.object_anchor,
                "contrast_pair": dossier.claim.contrast_pair.model_dump(mode="json"),
                "mechanism_term": dossier.claim.mechanism_term,
            },
            "material_notes": dossier.material_notes,
            "web_confirmations": [
                c.model_dump(mode="json") for c in dossier.web_confirmations if c.supports_claim
            ],
        },
        "audience": load_audience(),
        "story_brief": brief.model_dump(mode="json"),
        "must_include": {
            "proof_plan": [item.model_dump(mode="json") for item in brief.proof_plan],
            "idea_pitch": brief.idea_pitch,
            "hook_draft": brief.opening,
            "structure": [
                "hook 1-2 sentences",
                "facts/history/visual with connective tissue",
                "idea pitch Я бы / А если",
                "formula or question",
            ],
            "never_in_speech": [
                "автор книги",
                "название книги",
                "читаю у…",
                "по данным исследования",
            ],
        },
        "story_method": next(
            (m for m in _methods() if m.get("id") == brief.recommended_method), None
        ),
        "word_limit": {"min": lo, "max": hi},
    }
    text = ""
    words = 0
    for attempt in range(3):
        response = content_text(
            model.invoke(
                [
                    {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
                    {
                        "role": "user",
                        "content": str(
                            user
                            if attempt == 0
                            else {
                                **user,
                                "length_repair": (
                                    f"Вышло {words} слов; нужно строго {lo}–{hi}. "
                                    "Перепиши, сохранив только одну линию и три proof_plan."
                                ),
                            }
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
        words = len(re.findall(r"\S+", text))
        if lo <= words <= hi:
            break
    if not lo <= words <= hi:
        raise ValueError(f"D2: вышло {words} слов после retry; нужно {lo}–{hi}")
    return MonologueDraft(
        claim_id=dossier.claim_id,
        text=text,
        word_count=words,
        story_method=brief.recommended_method,
        ending_type=brief.ending_type,
    )
