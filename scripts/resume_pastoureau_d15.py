#!/usr/bin/env python3
"""Resume underwear run from D1.5 with cleaned primary source."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.costing import render_cost_report, summarize_calls
from edit.d1_visual_planner import plan_visual_scenario
from edit.d2_monologue import write_monologue
from edit.e_check import check_monologue
from edit.model_routing import get_personal_story_model
from edit.search import default_searcher
from models import ClaimCard, Dossier, HookOptions, StoryBrief, VisualResearchPack
from scripts.run_personal_full_audit import (
    AuditedLLM,
    dump,
    write_audit_md,
    write_call_trace,
)


def main() -> int:
    out = ROOT / "runs/pastoureau-cherny/produce-black-underwear-shift"
    claim = ClaimCard.model_validate(json.loads((out / "00_claim.json").read_text()))
    source = (out / "00_source_block.txt").read_text(encoding="utf-8")
    brief = StoryBrief.model_validate(json.loads((out / "01_story_brief.json").read_text()))
    hooks = HookOptions.model_validate(json.loads((out / "01b_hooks.json").read_text()))
    dossier = Dossier.model_validate(json.loads((out / "03_dossier.json").read_text()))
    visual_research = VisualResearchPack.model_validate(
        json.loads((out / "03a_visual_research.json").read_text())
    )

    # gemini: стабильнее на длинных стадиях после 500 у gpt-5-2
    base = get_personal_story_model(model="gemini-2.5-flash", temperature=0.2)
    audited = AuditedLLM(base, "gemini-2.5-flash")

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

    dump(out / "calls_resume_d15.json", audited.calls)
    cost = summarize_calls(audited.calls)
    dump(out / "06_cost.json", cost)
    (out / "COST.md").write_text(
        render_cost_report(cost, title=claim.claim_id), encoding="utf-8"
    )
    write_call_trace(out, audited.calls)
    write_audit_md(
        out / "AUDIT.md",
        claim_id=claim.claim_id,
        model="gemini-2.5-flash(D1.5→E)",
        monologue=monologue,
        check=check,
        hooks=hooks,
        brief=brief,
        cost_summary=cost,
        calls=audited.calls,
    )
    (out / "REPORT.md").write_text(
        "\n".join(
            [
                f"# Полный прогон · {claim.claim_id}",
                "",
                f"**E-check:** `passes={check.passes}`",
                f"**D2:** {monologue.word_count} слов · method `{monologue.story_method}`",
                f"**Cost (D1.5→E):** ${cost['cost_usd']:.4f}",
                "",
                "## Хук",
                "",
                hooks.variants[0].first_line,
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
    print("DONE", out)
    return 0 if check.passes else 2


if __name__ == "__main__":
    raise SystemExit(main())
