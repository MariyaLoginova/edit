#!/usr/bin/env python3
"""Resume personal audit from C1 using saved brief/hooks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.c1_material import collect_material
from edit.c1_research_enricher import enrich_material
from edit.costing import render_cost_report, summarize_calls
from edit.d1_visual_planner import plan_visual_scenario
from edit.d1_visual_research import research_visual_material
from edit.d2_monologue import write_monologue
from edit.e_check import check_monologue
from edit.model_routing import get_personal_story_model
from edit.search import default_searcher
from models import ClaimCard, HookOptions, SoftFactcheckResult, StoryBrief
from scripts.run_personal_full_audit import (
    AuditedLLM,
    PrimarySourceSearcher,
    dump,
    write_audit_csv,
    write_audit_md,
    write_call_trace,
)


def main() -> int:
    out = ROOT / "runs/pastoureau-cherny/produce-black-underwear-shift"
    claim = ClaimCard.model_validate(json.loads((out / "00_claim.json").read_text()))
    source = (out / "00_source_block.txt").read_text(encoding="utf-8")
    brief = StoryBrief.model_validate(json.loads((out / "01_story_brief.json").read_text()))
    hooks = HookOptions.model_validate(json.loads((out / "01b_hooks.json").read_text()))

    base = get_personal_story_model(model="gpt-5-2", temperature=0.2)
    audited = AuditedLLM(base, "gpt-5-2")
    searcher = PrimarySourceSearcher(
        source, "local://pastoureau-cherny", "Пастуро · Черный · нижнее белье"
    )

    print("== C1/C1.5 (resume) ==")
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

    print("== D1.4 ==")
    audited.stage = "D1.4 visual research"
    visual_research = research_visual_material(
        dossier,
        brief,
        primary_text=source,
        searcher=default_searcher(),
        llm=audited,
    )
    dump(out / "03a_visual_research.json", visual_research)

    print("== D1.5 ==")
    audited.stage = "D1.5 visual plan"
    visual_plan = plan_visual_scenario(
        dossier,
        brief,
        primary_text=source,
        visual_research=visual_research,
        image_searcher=default_searcher(),
        llm=audited,
    )
    dump(out / "03b_visual_scenario_plan.json", visual_plan)

    print("== D2 ==")
    audited.stage = "D2 monologue"
    monologue = write_monologue(
        dossier,
        brief,
        hook_text=hooks.variants[0].first_line,
        visual_plan=visual_plan,
        llm=audited,
    )
    dump(out / "04_monologue.json", monologue)
    print("WORDS=", monologue.word_count)
    print(monologue.text)

    print("== E-check ==")
    audited.stage = "E-check"
    check = check_monologue(
        monologue,
        dossier,
        brief=brief,
        visual_plan=visual_plan,
        llm=audited,
    )
    dump(out / "05_echeck.json", check)
    print("PASSES=", check.passes)
    print(check.summary)

    dump(out / "calls.json", audited.calls)
    write_audit_csv(out / "audit.csv", audited.calls, [])
    cost_summary = summarize_calls(audited.calls)
    dump(out / "06_cost.json", cost_summary)
    (out / "COST.md").write_text(
        render_cost_report(cost_summary, title=claim.claim_id), encoding="utf-8"
    )
    write_call_trace(out, audited.calls)
    write_audit_md(
        out / "AUDIT.md",
        claim_id=claim.claim_id,
        model="gpt-5-2(+failover)",
        monologue=monologue,
        check=check,
        hooks=hooks,
        brief=brief,
        cost_summary=cost_summary,
        calls=audited.calls,
    )
    (out / "REPORT.md").write_text(
        "\n".join(
            [
                f"# Полный прогон · {claim.claim_id}",
                "",
                f"**E-check:** `passes={check.passes}`",
                f"**D2:** {monologue.word_count} слов",
                f"**Cost resume:** ${cost_summary['cost_usd']:.4f}",
                "",
                "## Монолог",
                "",
                monologue.text,
                "",
                "## E-check",
                "",
                check.summary,
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("OUT", out)
    print("COST_USD", cost_summary["cost_usd"])
    print("FAILOVER", getattr(base, "events", []))
    return 0 if check.passes else 2


if __name__ == "__main__":
    raise SystemExit(main())
