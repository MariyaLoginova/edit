"""E7 · Идеатор: IdeaProbe поверх факта + вшивка в сценарий + HITL-гейт."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from edit.e2_retention_critic import script_as_timed_text
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import Dossier, IdeaProbe, ProbeRegister, ScriptDraft, ScriptLine

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e7_ideator.txt"

_HYPOTHESIS_MARKERS = re.compile(
    r"(\?|что если|а если|спекулятивно|гипотеза|можно ли читать|что если читать|"
    r"а что если|как будто|словно)",
    re.IGNORECASE,
)


def looks_like_hypothesis(text: str) -> bool:
    """Разгон должен быть вопросом-оптикой, не проверяемым фактом."""
    return bool(_HYPOTHESIS_MARKERS.search(text))


def validate_idea_probe(probe: IdeaProbe, dossier: Dossier) -> IdeaProbe:
    if probe.anchor_claim_id != dossier.claim_id:
        raise ValueError(
            f"E7: anchor_claim_id={probe.anchor_claim_id!r} нет в досье "
            f"({dossier.claim_id!r})"
        )
    if not probe.voiced_marker.strip():
        raise ValueError("E7: voiced_marker обязателен — иначе мнение сливается с фактом")
    if not looks_like_hypothesis(probe.probe_text):
        raise ValueError(
            "E7: probe_text должен быть вопросом/гипотезой, не утверждением факта"
        )
    # константа формата
    return probe.model_copy(update={"proposed": True})


def propose_idea_probe(
    dossier: Dossier,
    script: ScriptDraft,
    *,
    llm: ChatModel | None = None,
) -> IdeaProbe:
    if not dossier.frozen:
        raise ValueError("E7: досье должно быть заморожено")
    model = llm or get_chat_model(temperature=0.4)
    user = {
        "dossier": {
            "claim_id": dossier.claim_id,
            "claim": dossier.claim.model_dump(mode="json"),
            "material_notes": dossier.material_notes,
        },
        "script_id": script.script_id,
        "script_timed": script_as_timed_text(script),
        "registers": [r.value for r in ProbeRegister],
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    if isinstance(raw, dict):
        raw.setdefault("anchor_claim_id", dossier.claim_id)
        raw.setdefault("proposed", True)
    probe = IdeaProbe.model_validate(raw)
    return validate_idea_probe(probe, dossier)


def apply_probe_to_script(script: ScriptDraft, probe: IdeaProbe) -> ScriptDraft:
    """Вставляет маркированный разгон ПЕРЕД кодой (последней репликой)."""
    if not script.lines:
        raise ValueError("E7: пустой сценарий")
    if len(script.lines) == 1:
        body, coda = [], script.lines[0]
        t0, t1 = max(0.0, coda.t_start - 4.0), coda.t_start
    else:
        body = list(script.lines[:-1])
        coda = script.lines[-1]
        gap = max(2.0, min(6.0, (coda.t_start - body[-1].t_end) or 4.0))
        t0 = body[-1].t_end
        t1 = min(coda.t_start, t0 + gap)
        if t1 <= t0:
            t1 = t0 + 3.0
            coda = coda.model_copy(update={"t_start": t1})

    probe_line = ScriptLine(
        t_start=t0,
        t_end=t1,
        text=f"{probe.voiced_marker.strip()} {probe.probe_text.strip()}".strip(),
        claim_id=None,  # мнение — E1 пропускает по маркеру
        beat_id="e7_probe",
    )
    # если coda сдвинули — пересоберём хвост
    lines = [*body, probe_line, coda]
    duration = max(script.duration_sec, lines[-1].t_end)
    return script.model_copy(update={"lines": lines, "duration_sec": duration})


def parse_include_decision(raw: Any) -> bool:
    """Нормализует ответ человека с interrupt / Command(resume=...)."""
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in {"include", "yes", "y", "true", "1", "включить", "да"}:
            return True
        if v in {"exclude", "no", "n", "false", "0", "выключить", "нет"}:
            return False
        raise ValueError(f"E7 gate: не понял решение {raw!r}")
    if isinstance(raw, dict):
        if "include" in raw:
            return bool(raw["include"])
        if "decision" in raw:
            return parse_include_decision(raw["decision"])
    raise ValueError(f"E7 gate: неподдерживаемый resume payload: {raw!r}")
