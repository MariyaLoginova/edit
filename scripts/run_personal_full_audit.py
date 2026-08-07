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
            item["received"] = content_text(response)
            self.calls.append(item)
            return response
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
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


def write_audit_csv(path: Path, calls: list[dict[str, Any]], meta_rows: list[dict[str, str]]) -> None:
    rows = list(meta_rows)
    for idx, call in enumerate(calls, start=1):
        messages = call.get("messages") or []
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        rows.append(
            {
                "step": str(idx),
                "stage": str(call.get("stage") or ""),
                "model": str(call.get("model") or ""),
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
    parser.add_argument("--model", default="glm-5.2")
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
    hook = write_hook(brief, llm=audited)
    dump(out / "01b_hook.json", hook)

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
    monologue = write_monologue(dossier, brief, hook_text=hook.text, llm=audited)
    dump(out / "04_monologue.json", monologue)
    print(f"WORDS={monologue.word_count}")
    print(monologue.text)

    print("== E-check ==")
    audited.stage = "E-check"
    check = check_monologue(monologue, dossier, llm=audited)
    dump(out / "05_echeck.json", check)
    print(f"PASSES={check.passes}")
    print(check.summary)
    for issue in [*check.factual_issues, *check.overclaim_issues]:
        print(f"sev{issue.severity}: {issue.issue} :: {issue.quote}")

    dump(out / "calls.json", audited.calls)
    write_audit_csv(out / "audit.csv", audited.calls, meta_rows)

    report = [
        f"# Полный прогон · {claim.claim_id}",
        "",
        f"**Модель:** `{args.model}`",
        f"**Путь:** primary → E-editor → C1/C1.5 → D2 → E-check",
        f"**D2:** {monologue.word_count} слов · method `{monologue.story_method}`",
        f"**E-check:** `passes={check.passes}`",
        f"**LLM calls:** {len(audited.calls)}",
        "",
        "## Монолог",
        "",
        monologue.text,
        "",
        "## Хук",
        "",
        hook.text,
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
            f"Аудит: [`audit.csv`](audit.csv) · [`calls.json`](calls.json)",
        ]
    )
    (out / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(out / "audit.csv")
    return 0 if check.passes else 2


if __name__ == "__main__":
    raise SystemExit(main())
