"""Подсчёт стоимости LLM-вызовов по usage + config/pricing.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from edit.config import ROOT

PRICING_PATH = ROOT / "config" / "pricing.yaml"


def load_pricing() -> dict[str, Any]:
    return yaml.safe_load(PRICING_PATH.read_text(encoding="utf-8")) or {}


def extract_usage(response: Any) -> dict[str, int]:
    meta = getattr(response, "usage_metadata", None) or {}
    if isinstance(meta, dict) and meta:
        return {
            "input_tokens": int(meta.get("input_tokens") or 0),
            "output_tokens": int(meta.get("output_tokens") or 0),
            "total_tokens": int(
                meta.get("total_tokens")
                or (meta.get("input_tokens") or 0) + (meta.get("output_tokens") or 0)
            ),
        }
    resp_meta = getattr(response, "response_metadata", None) or {}
    token_usage = resp_meta.get("token_usage") if isinstance(resp_meta, dict) else None
    if isinstance(token_usage, dict):
        inp = int(token_usage.get("prompt_tokens") or 0)
        out = int(token_usage.get("completion_tokens") or 0)
        return {
            "input_tokens": inp,
            "output_tokens": out,
            "total_tokens": int(token_usage.get("total_tokens") or inp + out),
        }
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    pricing = load_pricing()
    rates = (pricing.get("models") or {}).get(model_id) or {}
    inp = float(rates.get("input_per_mtok") or 0.0)
    out = float(rates.get("output_per_mtok") or 0.0)
    return (input_tokens / 1_000_000.0) * inp + (output_tokens / 1_000_000.0) * out


def summarize_calls(calls: list[dict[str, Any]]) -> dict[str, Any]:
    by_stage: dict[str, dict[str, Any]] = {}
    total_in = total_out = 0
    total_cost = 0.0
    for call in calls:
        stage = str(call.get("stage") or "unknown")
        model = str(call.get("model") or "")
        usage = call.get("usage") or {}
        inp = int(usage.get("input_tokens") or 0)
        out = int(usage.get("output_tokens") or 0)
        usd = float(call.get("cost_usd") or cost_usd(model, inp, out))
        bucket = by_stage.setdefault(
            stage,
            {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "models": set(),
            },
        )
        bucket["calls"] += 1
        bucket["input_tokens"] += inp
        bucket["output_tokens"] += out
        bucket["cost_usd"] += usd
        bucket["models"].add(model)
        total_in += inp
        total_out += out
        total_cost += usd
    stages = {
        stage: {
            **{k: v for k, v in data.items() if k != "models"},
            "models": sorted(data["models"]),
            "cost_usd": round(data["cost_usd"], 6),
        }
        for stage, data in by_stage.items()
    }
    return {
        "currency": load_pricing().get("currency") or "USD",
        "calls": len(calls),
        "input_tokens": total_in,
        "output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "cost_usd": round(total_cost, 6),
        "by_stage": stages,
        "pricing_source": str(PRICING_PATH.relative_to(ROOT)),
    }


def render_cost_report(summary: dict[str, Any], *, title: str) -> str:
    lines = [
        f"# Cost · {title}",
        "",
        f"**Всего:** `${summary['cost_usd']:.4f}` · "
        f"{summary['calls']} LLM calls · "
        f"{summary['total_tokens']} tokens "
        f"(in {summary['input_tokens']} / out {summary['output_tokens']})",
        "",
        f"Прайс: `{summary['pricing_source']}`",
        "",
        "| stage | calls | input | output | USD |",
        "|---|---:|---:|---:|---:|",
    ]
    for stage, data in summary.get("by_stage", {}).items():
        lines.append(
            f"| {stage} | {data['calls']} | {data['input_tokens']} | "
            f"{data['output_tokens']} | ${data['cost_usd']:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)
