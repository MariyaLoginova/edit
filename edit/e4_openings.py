"""E4 · Перебор открытий: 5–8 вариантов первых 3 сек + выбор."""

from __future__ import annotations

from pathlib import Path

from edit.config import load_thresholds
from edit.e2_retention_critic import script_as_timed_text
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import Dossier, OpeningPick, RetentionReport, ScriptDraft, ScriptLine

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e4_openings.txt"


def _variant_bounds() -> tuple[int, int]:
    cfg = load_thresholds().get("editorial", {})
    return int(cfg.get("opening_variants_min", 5)), int(cfg.get("opening_variants_max", 8))


def _apply_opening(script: ScriptDraft, opening_text: str, *, horizon: float = 3.0) -> ScriptDraft:
    """Заменяет/схлопывает линии в первых horizon секундах в одну крючковую."""
    head: list[ScriptLine] = []
    tail: list[ScriptLine] = []
    claim_id = script.claim_id
    for line in script.lines:
        if line.t_end <= horizon + 1e-6 and line.t_start < horizon:
            head.append(line)
        elif line.t_start < horizon < line.t_end:
            # пересекает границу — уходит в tail с подрезанным стартом
            tail.append(line.model_copy(update={"t_start": horizon}))
        else:
            tail.append(line)

    new_head = ScriptLine(
        t_start=0.0,
        t_end=min(horizon, head[-1].t_end if head else horizon),
        text=opening_text,
        claim_id=claim_id,
        beat_id=head[0].beat_id if head else None,
    )
    lines = [new_head, *tail]
    return script.model_copy(update={"lines": lines})


def rewrite_openings(
    script: ScriptDraft,
    dossier: Dossier,
    retention: RetentionReport | None,
    *,
    llm: ChatModel | None = None,
) -> OpeningPick:
    if not dossier.frozen:
        raise ValueError("E4: нужен frozen dossier")
    model = llm or get_chat_model(temperature=0.4)
    vmin, vmax = _variant_bounds()
    user = {
        "variants_min": vmin,
        "variants_max": vmax,
        "claim": dossier.claim.model_dump(mode="json"),
        "retention": retention.model_dump(mode="json") if retention else None,
        "script": script.model_dump(mode="json"),
        "script_timed": script_as_timed_text(script),
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    if not isinstance(raw, dict):
        raise ValueError("E4: ожидался JSON-объект")
    raw.setdefault("script_id", script.script_id)
    # если LLM не вернул полный script — соберём сами из chosen
    if "script" not in raw or not isinstance(raw.get("script"), dict):
        pick_tmp = {
            "script_id": script.script_id,
            "variants": raw.get("variants", []),
            "chosen_index": raw.get("chosen_index", 0),
            "script": script.model_dump(mode="json"),
        }
        preview = OpeningPick.model_validate(pick_tmp)
        raw["script"] = _apply_opening(script, preview.chosen_text).model_dump(mode="json")
    else:
        # нормализуем id
        raw["script"]["script_id"] = script.script_id
        raw["script"]["claim_id"] = script.claim_id

    pick = OpeningPick.model_validate(raw)
    # гарантия: opening применён и claim_id не сбит
    fixed_script = _apply_opening(pick.script, pick.chosen_text)
    if fixed_script.claim_id != dossier.claim_id:
        raise ValueError("E4: script.claim_id уехал от досье")
    return pick.model_copy(update={"script": fixed_script})
