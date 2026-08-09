"""E6 · Сжатие −20–25% длины без потери смысла и claim_id."""

from __future__ import annotations

from pathlib import Path

from edit.config import load_thresholds
from edit.e2_retention_critic import script_as_timed_text
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import CompressionReport, RetentionReport, ScriptDraft

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e6_compress.txt"


def _char_count(script: ScriptDraft) -> int:
    return sum(len(line.text) for line in script.lines)


def _targets() -> tuple[float, float]:
    cfg = load_thresholds().get("editorial", {})
    return float(cfg.get("compress_min_ratio", 0.20)), float(cfg.get("compress_max_ratio", 0.25))


def finalize_compression(
    report: CompressionReport,
    original: ScriptDraft,
    *,
    min_ratio: float | None = None,
    max_ratio: float | None = None,
) -> CompressionReport:
    lo, hi = _targets()
    if min_ratio is not None:
        lo = min_ratio
    if max_ratio is not None:
        hi = max_ratio
    original_chars = _char_count(original)
    compressed_chars = _char_count(report.script)
    ratio = 0.0 if original_chars == 0 else 1.0 - (compressed_chars / original_chars)
    # claim_id не должны размножиться чужими
    bad_claim = any(
        line.claim_id not in (None, original.claim_id) for line in report.script.lines
    )
    passes = (lo - 0.02) <= ratio <= (hi + 0.05) and not bad_claim and bool(report.script.lines)
    return report.model_copy(
        update={
            "script_id": original.script_id,
            "original_chars": original_chars,
            "compressed_chars": compressed_chars,
            "reduction_ratio": round(ratio, 4),
            "passes": passes,
            "script": report.script.model_copy(
                update={
                    "script_id": original.script_id,
                    "claim_id": original.claim_id,
                    "duration_sec": report.script.duration_sec or original.duration_sec,
                }
            ),
        }
    )


def compress_script(
    script: ScriptDraft,
    retention: RetentionReport | None = None,
    *,
    llm: ChatModel | None = None,
) -> CompressionReport:
    model = llm or get_chat_model(temperature=0.2)
    lo, hi = _targets()
    user = {
        "target_reduction_min": lo,
        "target_reduction_max": hi,
        "retention": retention.model_dump(mode="json") if retention else None,
        "script": script.model_dump(mode="json"),
        "script_timed": script_as_timed_text(script),
        "original_chars": _char_count(script),
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(user)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    if isinstance(raw, dict):
        raw.setdefault("script_id", script.script_id)
        raw.setdefault("original_chars", _char_count(script))
        raw.setdefault("compressed_chars", 0)
        raw.setdefault("reduction_ratio", 0.0)
        raw.setdefault("passes", False)
        raw.setdefault("summary", "")
    report = CompressionReport.model_validate(raw)
    return finalize_compression(report, script, min_ratio=lo, max_ratio=hi)
