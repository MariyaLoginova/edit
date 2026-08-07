#!/usr/bin/env python3
"""Полный личный контур с аудитом вызовов (E-editor → C1/C1.5 → D2 → E-check)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from edit.c1_material import collect_material
from edit.c1_research_enricher import enrich_material
from edit.costing import (
    cost_usd,
    extract_usage,
    render_cost_report,
    summarize_calls,
)
from edit.d2_monologue import write_monologue
from edit.e_check import check_monologue
from edit.e_editor import plan_story
from edit.e_hook import write_hook
from edit.llm import content_text, get_chat_model
from edit.search import SearchHit
from models import ClaimCard, SoftFactcheckResult

load_dotenv(ROOT / ".env")


@dataclass
class AuditedLLM:
    model: Any
    model_id: str
    stage: str = ""
    calls: list[dict[str, Any]] = field(default_factory=list)

    def invoke(self, messages: list[dict[str, str]]) -> Any:
        item: dict[str, Any] = {
            "model": self.model_id,
            "stage": self.stage,
            "messages": messages,
        }
        try:
            response = self.model.invoke(messages)
            usage = extract_usage(response)
            item["received"] = content_text(response)
            item["usage"] = usage
            item["cost_usd"] = round(
                cost_usd(
                    self.model_id,
                    usage["input_tokens"],
                    usage["output_tokens"],
                ),
                6,
            )
            self.calls.append(item)
            return response
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
            item["usage"] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            item["cost_usd"] = 0.0
            self.calls.append(item)
            raise


class PrimarySourceSearcher:
    def __init__(self, source: str, url: str, title: str):
        self.source = source
        self.url = url
        self.title = title

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        return [
            SearchHit(url=self.url, title=self.title, snippet=self.source),
        ]


def dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_claim(claim_path: Path, claim_id: str | None) -> ClaimCard:
    raw = json.loads(claim_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "claims" in raw:
        claims = raw["claims"]
        if claim_id:
            for item in claims:
                if item.get("claim_id") == claim_id:
                    return ClaimCard.model_validate(item)
            raise SystemExit(f"claim_id не найден: {claim_id}")
        return ClaimCard.model_validate(claims[0])
    return ClaimCard.model_validate(raw)


def _clip(text: str, limit: int = 4000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n\n… [{len(text) - limit} chars truncated]"


def write_call_trace(out_dir: Path, calls: list[dict[str, Any]]) -> Path:
    """Полный след: на каждый LLM-вызов — md с system / user / received."""
    calls_dir = out_dir / "calls"
    calls_dir.mkdir(parents=True, exist_ok=True)
    index: list[str] = [
        "# Call trace · prompts → answers",
        "",
        f"**Calls:** {len(calls)}",
        "",
    ]
    for idx, call in enumerate(calls, start=1):
        messages = call.get("messages") or []
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        received = str(call.get("received") or "")
        usage = call.get("usage") or {}
        stage = str(call.get("stage") or "unknown")
        model = str(call.get("model") or "")
        slug = f"{idx:02d}_{stage.lower().replace(' ', '_').replace('/', '-')}"
        md_path = calls_dir / f"{slug}.md"
        json_path = calls_dir / f"{slug}.json"
        dump(
            json_path,
            {
                "step": idx,
                "stage": stage,
                "model": model,
                "usage": usage,
                "cost_usd": call.get("cost_usd"),
                "error": call.get("error"),
                "system_prompt": system,
                "user_payload": user,
                "received": received,
            },
        )
        md_path.write_text(
            "\n".join(
                [
                    f"# Call {idx} · {stage}",
                    "",
                    f"**Model:** `{model}`",
                    f"**Tokens:** in {usage.get('input_tokens', 0)} / "
                    f"out {usage.get('output_tokens', 0)}",
                    f"**Cost:** `${float(call.get('cost_usd') or 0):.6f}`",
                    f"**Error:** {call.get('error') or '—'}",
                    "",
                    "## System prompt",
                    "",
                    "```",
                    system.strip(),
                    "```",
                    "",
                    f"## User payload ({len(user)} chars)",
                    "",
                    "```",
                    _clip(user, 6000),
                    "```",
                    "",
                    f"## Received ({len(received)} chars)",
                    "",
                    "```",
                    received.strip() or "(empty)",
                    "```",
                    "",
                    f"Full JSON: [`{json_path.name}`]({json_path.name})",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        index.append(
            f"- [{idx:02d} {stage}]({md_path.name}) · `{model}` · "
            f"${float(call.get('cost_usd') or 0):.4f}"
        )
    index.append("")
    (calls_dir / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return calls_dir


def write_audit_md(
    path: Path,
    *,
    claim_id: str,
    model: str,
    monologue: Any,
    check: Any,
    hooks: Any,
    brief: Any,
    cost_summary: dict[str, Any],
    calls: list[dict[str, Any]],
) -> None:
    mono_text = getattr(monologue, "text", None) or (monologue or {}).get("text", "")
    words = getattr(monologue, "word_count", None) or (monologue or {}).get("word_count", "?")
    method = getattr(monologue, "story_method", None) or (monologue or {}).get("story_method", "?")
    passes = getattr(check, "passes", None)
    if passes is None and isinstance(check, dict):
        passes = check.get("passes")
    hook0 = ""
    if hooks is not None:
        variants = getattr(hooks, "variants", None) or hooks.get("variants") or []
        if variants:
            v0 = variants[0]
            hook0 = getattr(v0, "first_line", None) or v0.get("first_line", "")
    main_thought = getattr(brief, "main_thought", None) or (brief or {}).get("main_thought", "")
    angle = getattr(brief, "angle", None) or (brief or {}).get("angle", "")
    why_viewer = getattr(brief, "why_viewer", None) or (brief or {}).get("why_viewer", "")
    idea_pitch = getattr(brief, "idea_pitch", None) or (brief or {}).get("idea_pitch", "")
    lines = [
        f"# Аудит · {claim_id}",
        "",
        f"**Модель:** `{model}`",
        f"**D2:** {words} слов · method `{method}`",
        f"**E-check:** `passes={passes}`",
        f"**Cost:** `${cost_summary.get('cost_usd', 0):.4f}` · "
        f"{cost_summary.get('total_tokens', 0)} tokens · "
        f"{cost_summary.get('calls', 0)} LLM calls",
        "",
        "## Цепочка",
        "",
        "primary → E-editor → E-hook → C1/C1.5 → D2 → E-check",
        "",
        "## Brief",
        "",
        f"- **format:** {getattr(brief, 'format', None) or (brief or {}).get('format', '')}",
        f"- **main_thought:** {main_thought}",
        f"- **angle:** {angle}",
        f"- **why_viewer (служебно):** {why_viewer}",
        f"- **conclusion.plain:** {getattr(getattr(brief, 'conclusion', None), 'plain', None) or ''}",
        f"- **idea_pitch:** {idea_pitch}",
        f"- **selected hook:** {hook0}",
        "",
        "## Монолог",
        "",
        mono_text,
        "",
        "## Cost by stage",
        "",
        "| stage | calls | input | output | USD |",
        "|---|---:|---:|---:|---:|",
    ]
    for stage, data in (cost_summary.get("by_stage") or {}).items():
        lines.append(
            f"| {stage} | {data['calls']} | {data['input_tokens']} | "
            f"{data['output_tokens']} | ${data['cost_usd']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## LLM calls · prompts → answers",
            "",
            "Полный след каждого вызова: [`calls/README.md`](calls/README.md)",
            "",
        ]
    )
    for idx, call in enumerate(calls, start=1):
        messages = call.get("messages") or []
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        received = str(call.get("received") or "")
        usage = call.get("usage") or {}
        stage = call.get("stage") or ""
        lines.extend(
            [
                f"### {idx}. {stage} · `{call.get('model')}`",
                "",
                f"tokens in/out: {usage.get('input_tokens', 0)} / "
                f"{usage.get('output_tokens', 0)} · "
                f"${float(call.get('cost_usd') or 0):.4f}",
                "",
                "<details><summary>system prompt</summary>",
                "",
                "```",
                _clip(system, 2500),
                "```",
                "",
                "</details>",
                "",
                f"<details><summary>user payload ({len(user)} chars)</summary>",
                "",
                "```",
                _clip(user, 3500),
                "```",
                "",
                "</details>",
                "",
                "<details><summary>received</summary>",
                "",
                "```",
                _clip(received, 5000),
                "```",
                "",
                "</details>",
                "",
            ]
        )
    lines.extend(
        [
            "## E-check",
            "",
            f"```json\n{json.dumps(check.model_dump(mode='json') if hasattr(check, 'model_dump') else check, ensure_ascii=False, indent=2)}\n```",
            "",
            "Артефакты: [`audit.csv`](audit.csv) · [`calls.json`](calls.json) · "
            "[`COST.md`](COST.md) · [`calls/`](calls/)",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_audit_csv(path: Path, calls: list[dict[str, Any]], meta_rows: list[dict[str, str]]) -> None:
    rows = list(meta_rows)
    for idx, call in enumerate(calls, start=1):
        messages = call.get("messages") or []
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        usage = call.get("usage") or {}
        rows.append(
            {
                "step": str(idx),
                "stage": str(call.get("stage") or ""),
                "model": str(call.get("model") or ""),
                "input_tokens": str(usage.get("input_tokens") or 0),
                "output_tokens": str(usage.get("output_tokens") or 0),
                "cost_usd": str(call.get("cost_usd") or 0),
                "system_prompt": system,
                "user_payload": user,
                "received": str(call.get("received") or ""),
                "error": str(call.get("error") or ""),
            }
        )
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "step",
                "stage",
                "model",
                "input_tokens",
                "output_tokens",
                "cost_usd",
                "system_prompt",
                "user_payload",
                "received",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claim", type=Path, required=True)
    parser.add_argument("--claim-id", default=None)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5-2")
    parser.add_argument("--source-url", default="local://primary")
    parser.add_argument("--source-title", default="Первичный текст")
    args = parser.parse_args()

    claim = load_claim(args.claim, args.claim_id)
    source = args.source.read_text(encoding="utf-8")
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    dump(out / "00_claim.json", claim)
    (out / "00_source_block.txt").write_text(source, encoding="utf-8")

    base = get_chat_model(model=args.model, temperature=0.2)
    audited = AuditedLLM(base, args.model)
    searcher = PrimarySourceSearcher(source, args.source_url, args.source_title)
    meta_rows: list[dict[str, str]] = [
        {
            "step": "0",
            "stage": "input",
            "model": "n/a",
            "input_tokens": "0",
            "output_tokens": "0",
            "cost_usd": "0",
            "system_prompt": "",
            "user_payload": f"claim_id={claim.claim_id}; source={args.source}",
            "received": f"chars={len(source)}",
            "error": "",
        }
    ]

    print("== E-editor ==")
    audited.stage = "E-editor"
    brief = plan_story(claim, primary_text=source, llm=audited)
    dump(out / "01_story_brief.json", brief)
    audited.stage = "E-hook"
    hooks = write_hook(brief, llm=audited)
    dump(out / "01b_hooks.json", hooks)

    print("== C1/C1.5 ==")
    draft = collect_material(
        claim,
        searcher=searcher,
        llm=None,
        primary_text=source,
        research_queries=brief.research_queries,
    )
    audited.stage = "C1.5 research enricher"
    enriched, pack = enrich_material(draft, brief, llm=audited)
    dossier = enriched.model_copy(
        update={
            "soft_factcheck": SoftFactcheckResult(
                ok=True,
                rationale="Первичный текст и C1.5 material переданы E-check.",
            )
        }
    ).freeze(require_images=False)
    dump(out / "02_research_pack.json", pack)
    dump(out / "03_dossier.json", dossier)

    print("== D2 ==")
    audited.stage = "D2 monologue"
    monologue = write_monologue(
        dossier,
        brief,
        hook_text=hooks.variants[0].first_line,
        llm=audited,
    )
    dump(out / "04_monologue.json", monologue)
    print(f"WORDS={monologue.word_count}")
    print(monologue.text)

    print("== E-check ==")
    audited.stage = "E-check"
    check = check_monologue(monologue, dossier, brief=brief, llm=audited)
    dump(out / "05_echeck.json", check)
    print(f"PASSES={check.passes}")
    print(check.summary)
    for issue in [*check.factual_issues, *check.overclaim_issues]:
        print(f"sev{issue.severity}: {issue.issue} :: {issue.quote}")

    dump(out / "calls.json", audited.calls)
    write_audit_csv(out / "audit.csv", audited.calls, meta_rows)
    cost_summary = summarize_calls(audited.calls)
    dump(out / "06_cost.json", cost_summary)
    (out / "COST.md").write_text(
        render_cost_report(cost_summary, title=claim.claim_id),
        encoding="utf-8",
    )
    write_call_trace(out, audited.calls)
    write_audit_md(
        out / "AUDIT.md",
        claim_id=claim.claim_id,
        model=args.model,
        monologue=monologue,
        check=check,
        hooks=hooks,
        brief=brief,
        cost_summary=cost_summary,
        calls=audited.calls,
    )

    report = [
        f"# Полный прогон · {claim.claim_id}",
        "",
        f"**Модель:** `{args.model}`",
        f"**Путь:** primary → E-editor → C1/C1.5 → D2 → E-check",
        f"**D2:** {monologue.word_count} слов · method `{monologue.story_method}`",
        f"**E-check:** `passes={check.passes}`",
        f"**LLM calls:** {len(audited.calls)}",
        f"**Cost:** `${cost_summary['cost_usd']:.4f}` · "
        f"{cost_summary['total_tokens']} tokens",
        "",
        "## Монолог",
        "",
        monologue.text,
        "",
        "## Выбранный хук",
        "",
        hooks.variants[0].first_line,
        "",
        "## E-check summary",
        "",
        check.summary,
        "",
        "## Idea pitch (brief)",
        "",
        brief.idea_pitch or "—",
        "",
        "## Research gaps",
        "",
    ]
    if pack.gaps:
        report.extend(f"- {gap}" for gap in pack.gaps)
    else:
        report.append("- нет")
    report.extend(
        [
            "",
            "Аудит: [`audit.csv`](audit.csv) · [`calls.json`](calls.json) · "
            "[`COST.md`](COST.md)",
        ]
    )
    (out / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    # idea_pitch — в банк идей, чтобы сильные, но не выбранные линии не терялись.
    if brief.idea_pitch:
        bank = ROOT / "runs" / "goralik-barbie" / "IDEA_BANK.md"
        if bank.parent.is_dir():
            entry = (
                f"\n## {claim.claim_id} · idea_pitch\n\n"
                f"**Прогон:** `{out.name}` · angle: {brief.angle}\n\n"
                f"{brief.idea_pitch}\n"
            )
            existing = bank.read_text(encoding="utf-8") if bank.exists() else "# Банк идей\n"
            if brief.idea_pitch not in existing:
                bank.write_text(existing.rstrip() + "\n" + entry, encoding="utf-8")

    print(out / "audit.csv")
    print(f"COST_USD={cost_summary['cost_usd']:.4f}")
    return 0 if check.passes else 2


if __name__ == "__main__":
    raise SystemExit(main())
