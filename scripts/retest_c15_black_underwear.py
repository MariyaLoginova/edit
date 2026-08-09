#!/usr/bin/env python3
"""Перепрогон C1+C1.5 для black-underwear-shift (чёрный как эротический цвет).

Ровно 1 LLM-вызов (C1.5). C1 — код + Brave Search.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.c1_material import collect_material
from edit.c1_research_enricher import enrich_material
from edit.model_routing import get_personal_story_model
from edit.search import EmptySearcher, SearchUnavailableError, require_web_searcher, web_search_enabled
from models import ClaimCard, SoftFactcheckResult, StoryBrief
from scripts.run_personal_full_audit import AuditedLLM, dump


def main() -> int:
    out = ROOT / "runs/pastoureau-cherny/produce-black-underwear-shift"
    claim = ClaimCard.model_validate(json.loads((out / "00_claim.json").read_text()))
    source = (out / "00_source_block.txt").read_text(encoding="utf-8")
    brief = StoryBrief.model_validate(json.loads((out / "01_story_brief.json").read_text()))

    print("web_search_enabled=", web_search_enabled())
    try:
        searcher = require_web_searcher()
        mode = "brave"
    except SearchUnavailableError as exc:
        print("WARN:", exc)
        print("Falling back to EmptySearcher (primary_text only, no fake web hits).")
        searcher = EmptySearcher()
        mode = "primary-only"

    print("== C1 collect_material ==")
    draft = collect_material(
        claim,
        searcher=searcher,
        llm=None,
        primary_text=source,
        research_queries=brief.research_queries,
    )
    print("web_confirmations=", len(draft.web_confirmations))
    for item in draft.web_confirmations[:12]:
        print(f"  - {item.url[:80]} | {item.title[:60]}")

    print("== C1.5 enrich_material (1 LLM call) ==")
    base = get_personal_story_model(model="gpt-5-2", temperature=0.0)
    audited = AuditedLLM(base, "gpt-5-2")
    audited.stage = "C1.5 research enricher"
    enriched, pack = enrich_material(draft, brief, llm=audited)
    dossier = enriched.model_copy(
        update={
            "soft_factcheck": SoftFactcheckResult(
                ok=True,
                rationale="C1.5 retest: primary + web enrichment.",
            )
        }
    ).freeze(require_images=False)

    dump(out / "02_research_pack.json", pack)
    dump(out / "03_dossier.json", dossier)
    dump(
        out / "02_research_pack.meta.json",
        {
            "search_mode": mode,
            "web_hits": len(draft.web_confirmations),
            "llm_calls": len(audited.calls),
        },
    )
    dump(out / "calls_c15_retest.json", audited.calls)

    print("FACTS=", len(pack.facts))
    for i, fact in enumerate(pack.facts, 1):
        print(f"{i}. [{fact.source_url}] {fact.fact}")
    print("GAPS=", pack.gaps)
    print("SUMMARY=", pack.summary)
    print("LLM_CALLS=", len(audited.calls))
    print("DONE", out / "02_research_pack.json")
    return 0 if pack.facts else 2


if __name__ == "__main__":
    raise SystemExit(main())
