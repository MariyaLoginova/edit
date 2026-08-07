"""D2 FIX-5: личный plain-text монолог вместо JSON-сценария."""

from __future__ import annotations

import re
from pathlib import Path

from edit.audience import load_audience
from edit.config import ROOT, load_thresholds
from edit.llm import ChatModel, content_text
from edit.model_routing import PolicyBlockedError, get_personal_story_model, is_policy_text
from models import Dossier, MonologueDraft, StoryBrief, can_freeze

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d2_monologue.txt"
METHODS_PATH = ROOT / "config" / "story_methods.yaml"
_FIRST_PERSON = re.compile(r"\b(я|мне|меня|мной|увидела|заметила|прочитала)\b", re.I)
_WRITING_ENVELOPE = re.compile(
    r"^:::writing[^\n]*\n?|^:::\s*$", re.MULTILINE | re.IGNORECASE
)
_MONOLOGUE_LABEL = re.compile(r"(?im)^\s*готовый\s+монолог\s*:\s*")
_STOP_PHRASES = ("формула простая", "механизм:", "в материале", "как сказано")


def _word_bounds() -> tuple[int, int]:
    cfg = load_thresholds().get("scenario", {})
    # Целимся в 105–115, но речь живого автора может быть чуть медленнее.
    return int(cfg.get("min_words", 90)), int(cfg.get("max_words", 120))


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
            "claim": dossier.claim.model_dump(mode="json"),
            "material_notes": dossier.material_notes,
            "web_confirmations": [
                c.model_dump(mode="json") for c in dossier.web_confirmations if c.supports_claim
            ],
        },
        "audience": load_audience(),
        "story_brief": brief.model_dump(mode="json"),
        "story_method": next(
            (m for m in _methods() if m.get("id") == brief.recommended_method), None
        ),
        "word_limit": {"min": lo, "max": hi},
    }
    text = content_text(
        model.invoke(
            [
                {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": str(user)},
            ]
        )
    ).strip()
    if is_policy_text(text):
        raise PolicyBlockedError(text)
    text = re.sub(r"^```.*?\n|\n```$", "", text, flags=re.S).strip()
    text = _MONOLOGUE_LABEL.sub("", text).strip()
    text = _WRITING_ENVELOPE.sub("", text).strip()
    text = re.sub(r"\bформула\s+простая\s*:\s*", "", text, flags=re.I)
    words = len(re.findall(r"\S+", text))
    # Длина и первое лицо оцениваются E-проверкой. Не сжигаем API на
    # идентичном D2-повторе только из-за 32 или 121 слова.
    return MonologueDraft(
        claim_id=dossier.claim_id,
        text=text,
        word_count=words,
        story_method=brief.recommended_method,
        ending_type=brief.ending_type,
    )
