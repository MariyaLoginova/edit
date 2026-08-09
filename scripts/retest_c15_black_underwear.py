#!/usr/bin/env python3
"""C1.5 retest: Gemini + googleSearch на KIE для black-underwear-shift.

1 LLM-вызов (возможен 1 repair). Статья/бриф — контекст; факты — новые с сети.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.c1_material import collect_material
from edit.c1_research_enricher import enrich_material
from edit.model_routing import get_research_enrich_model
from edit.search import EmptySearcher
from models import ClaimCard, SoftFactcheckResult, StoryBrief
from scripts.run_personal_full_audit import AuditedLLM, dump


def main() -> int:
    out = ROOT / "runs/pastoureau-cherny/produce-black-underwear-shift"
    claim = ClaimCard.model_validate(json.loads((out / "00_claim.json").read_text()))
    source = (out / "00_source_block.txt").read_text(encoding="utf-8")
    brief = StoryBrief.model_validate(json.loads((out / "01_story_brief.json").read_text()))

    print("== C1 collect_material (primary only; web идёт внутри C1.5/KIE) ==")
    draft = collect_material(
        claim,
        searcher=EmptySearcher(),
        llm=None,
        primary_text=source,
        research_queries=brief.research_queries,
    )
    print("web_confirmations=", len(draft.web_confirmations))

    print("== C1.5 googleSearch enrich ==")
    base = get_research_enrich_model(temperature=0.2)
    audited = AuditedLLM(base, "research-enrich-failover")
    audited.stage = "C1.5 research enricher"
    enriched, pack = enrich_material(draft, brief, llm=audited)
    dossier = enriched.model_copy(
        update={
            "soft_factcheck": SoftFactcheckResult(
                ok=True,
                rationale="C1.5 googleSearch retest.",
            )
        }
    ).freeze(require_images=False)

    dump(out / "02_research_pack.json", pack)
    dump(out / "03_dossier.json", dossier)
    dump(
        out / "02_research_pack.meta.json",
        {
            "search_mode": "kie-googleSearch",
            "llm_calls": len(audited.calls),
            "tools": (audited.calls[0].get("tools") if audited.calls else None),
        },
    )
    dump(out / "calls_c15_retest.json", audited.calls)

    print("FACTS=", len(pack.facts))
    for i, fact in enumerate(pack.facts, 1):
        print(f"{i}. [{fact.source_url}] {fact.fact}")
    print("GAPS=", pack.gaps)
    print("SUMMARY=", pack.summary)
    print("LLM_CALLS=", len(audited.calls))
    for call in audited.calls:
        print("  stage=", call.get("stage"), "tools=", bool(call.get("tools")), "err=", call.get("error"))
    print("DONE", out / "02_research_pack.json")
    return 0 if pack.facts else 2


if __name__ == "__main__":
    raise SystemExit(main())
