"""D2 · Голос за кадром: озвучка + таймкоды из досье (FIX-4, без D1/D3)."""

from __future__ import annotations

from pathlib import Path
import re

from edit.config import load_thresholds
from edit.llm import ChatModel, get_chat_model, invoke_json
from models import Dossier, ScriptDraft, can_freeze

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "d2_prose.txt"

DEFAULT_STOP = [
    "странно, но",
    "формула простая",
    "заметь",
    "через миг",
    "на самом деле всё просто",
    "а теперь представь",
    "механизм:",
    "формула:",
    "в материале",
    "в сниппете",
    "как сказано",
    "считывается как",
]
_OPINION_MARKER = re.compile(r"^\s*а если\b|^\s*моя интерпретация\b", re.IGNORECASE)


def _stop_phrases() -> list[str]:
    cfg = load_thresholds().get("scenario", {}).get("meta_stop_phrases") or []
    return list(dict.fromkeys([*DEFAULT_STOP, *[str(x).lower() for x in cfg]]))


def _duration_bounds() -> tuple[float, float, float]:
    cfg = load_thresholds().get("scenario", {})
    return (
        float(cfg.get("min_duration_sec", 38)),
        float(cfg.get("target_duration_sec", 45)),
        float(cfg.get("max_duration_sec", 52)),
    )


def write_prose(
    dossier: Dossier,
    beats=None,  # noqa: ANN001 — совместимость со старыми вызовами; игнорируется
    *,
    llm: ChatModel | None = None,
    script_id: str | None = None,
) -> ScriptDraft:
    """Пишет озвучку сразу голосом; сам расставляет таймкоды (FIX-4)."""
    if not dossier.frozen:
        raise ValueError("D2 пишет только из замороженного досье")
    ok, problems = can_freeze(dossier, require_images=False)
    if not ok:
        raise ValueError(
            "D2: досье неполное (обход freeze?) — " + "; ".join(problems)
        )

    claim = dossier.claim
    stop = _stop_phrases()
    d_min, d_target, d_max = _duration_bounds()
    sid = script_id or f"script-{dossier.claim_id}"
    model = llm or get_chat_model(temperature=0.2)
    user = {
        "dossier": {
            "claim_id": dossier.claim_id,
            "claim": claim.claim,
            "counter_expectation": claim.counter_expectation,
            "mechanism_term": claim.mechanism_term,
            "mechanism_explain": claim.mechanism_explain,
            "citation": claim.citation.model_dump(mode="json"),
            "scope": claim.scope.model_dump(mode="json"),
            "material_notes": dossier.material_notes,
            "web_confirmations": [
                {"title": c.title, "snippet": c.snippet}
                for c in dossier.web_confirmations
                if c.supports_claim
            ],
        },
        "target_duration_sec": d_target,
        "min_duration_sec": d_min,
        "max_duration_sec": d_max,
    }
    last_err: Exception | None = None
    for _attempt in range(3):
        payload = user
        if last_err is not None:
            payload = {
                **user,
                "revision_note": (
                    f"Отклонено валидатором: {last_err}. "
                    "Перепиши без этой проблемы; сохрани живой голос и таймкоды."
                ),
            }
        raw = invoke_json(
            model,
            [
                {
                    "role": "system",
                    "content": PROMPT_PATH.read_text(encoding="utf-8").strip(),
                },
                {"role": "user", "content": str(payload)},
            ],
            retries=2,
        )
        if isinstance(raw, dict):
            raw.setdefault("script_id", sid)
            raw.setdefault("claim_id", dossier.claim_id)
            raw["tov_applied"] = True  # голос заложен в D2 (бывш. D3)
            for line in raw.get("lines") or []:
                if isinstance(line, dict):
                    # Гипотеза в финале должна быть слышна как мнение, не факт.
                    if _OPINION_MARKER.search(str(line.get("text", ""))):
                        line["claim_id"] = None
                    elif not line.get("claim_id"):
                        line["claim_id"] = dossier.claim_id
        try:
            script = ScriptDraft.model_validate(raw)
            _assert_claim_ids(script, dossier)
            _assert_duration(script, d_min, d_max)
            _assert_no_stop_phrases(script, stop)
            return script
        except (ValueError, Exception) as exc:
            last_err = exc
    assert last_err is not None
    raise last_err


def _assert_claim_ids(script: ScriptDraft, dossier: Dossier) -> None:
    if script.claim_id != dossier.claim_id:
        raise ValueError("D2: script.claim_id не из досье")
    for line in script.lines:
        if line.claim_id is None:
            continue
        if line.claim_id != dossier.claim_id:
            raise ValueError(
                f"D2: line с чужим claim_id={line.claim_id!r} — факт вне досье"
            )


def _assert_duration(script: ScriptDraft, d_min: float, d_max: float) -> None:
    if not (d_min - 0.5 <= script.duration_sec <= d_max + 0.5):
        raise ValueError(
            f"D2: duration_sec={script.duration_sec} вне [{d_min}, {d_max}]"
        )


def _assert_no_stop_phrases(script: ScriptDraft, stop: list[str]) -> None:
    joined = " ".join(line.text.lower() for line in script.lines)
    for phrase in stop:
        if phrase.lower() in joined:
            raise ValueError(f"D2: стоп-фраза мета-связки в озвучке: {phrase!r}")


