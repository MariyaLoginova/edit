#!/usr/bin/env python3
"""Прогоны EDIT: A2 / материал C / E1 / E2 / полный срез вехи 2.

Примеры:
  python scripts/run_vertical_slice.py a2 tests/fixtures/fashion_theory_segment.json
  python scripts/run_vertical_slice.py e2 tests/fixtures/script_weak.json
  python scripts/run_vertical_slice.py material --claim-json claim.json
  python scripts/run_vertical_slice.py v2 \\
      --source tests/fixtures/fashion_theory_segment.json \\
      --script tests/fixtures/script_strong.json \\
      --claim-id lbd-maintenance-not-luxury
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.graph import (
    build_a2_only_graph,
    build_e1_only_graph,
    build_e2_only_graph,
    build_material_graph,
    build_v2_slice_graph,
    build_vertical_slice_graph,
)
from models import ClaimCard, Dossier, ScriptDraft, SourceMap


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="EDIT — прогон узлов/срезов")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_a2 = sub.add_parser("a2", help="Майнер тезисов")
    p_a2.add_argument("source_map", type=Path)

    p_e2 = sub.add_parser("e2", help="Критик удержания")
    p_e2.add_argument("script", type=Path)

    p_e1 = sub.add_parser("e1", help="Аудитор трассируемости")
    p_e1.add_argument("script", type=Path)
    p_e1.add_argument("dossier", type=Path, help="JSON замороженного Dossier")

    p_mat = sub.add_parser("material", help="C1→C2→C3(+freeze)")
    p_mat.add_argument("--claim-json", type=Path, required=True)

    p_v1 = sub.add_parser("slice", help="Веха 1: A2→B2→E2")
    p_v1.add_argument("--source", type=Path, required=True)
    p_v1.add_argument("--script", type=Path, required=True)
    p_v1.add_argument("--claim-id", default=None)

    p_v2 = sub.add_parser("v2", help="Веха 2: A2→C→E1→E2")
    p_v2.add_argument("--source", type=Path, required=True)
    p_v2.add_argument("--script", type=Path, required=True)
    p_v2.add_argument("--claim-id", default=None)

    args = p.parse_args()

    if args.cmd == "a2":
        source = SourceMap.model_validate(_load_json(args.source_map))
        out = build_a2_only_graph().invoke({"source_map": source})
        print(json.dumps([c.model_dump(mode="json") for c in out["claims"]], ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "e2":
        script = ScriptDraft.model_validate(_load_json(args.script))
        out = build_e2_only_graph().invoke({"script": script})
        report = out["retention"]
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0 if report.passes else 2

    if args.cmd == "e1":
        script = ScriptDraft.model_validate(_load_json(args.script))
        dossier = Dossier.model_validate(_load_json(args.dossier))
        out = build_e1_only_graph().invoke({"script": script, "dossier": dossier})
        print(json.dumps(out["trace"].model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0 if out["trace"].passes else 2

    if args.cmd == "material":
        claim = ClaimCard.model_validate(_load_json(args.claim_json))
        out = build_material_graph().invoke(
            {"claims": [claim], "selected_claim_id": claim.claim_id}
        )
        d = out["dossier"]
        print(json.dumps(d.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0 if d.frozen else 2

    if args.cmd == "slice":
        source = SourceMap.model_validate(_load_json(args.source))
        script = ScriptDraft.model_validate(_load_json(args.script))
        out = build_vertical_slice_graph().invoke(
            {
                "source_map": source,
                "script": script,
                "selected_claim_id": args.claim_id,
            }
        )
        payload = {
            "claims": [c.model_dump(mode="json") for c in out.get("claims") or []],
            "retention": out["retention"].model_dump(mode="json") if out.get("retention") else None,
            "blocked_for_production": out.get("blocked_for_production"),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if not out.get("blocked_for_production") else 2

    # v2
    source = SourceMap.model_validate(_load_json(args.source))
    script = ScriptDraft.model_validate(_load_json(args.script))
    out = build_v2_slice_graph().invoke(
        {
            "source_map": source,
            "script": script,
            "selected_claim_id": args.claim_id,
        }
    )
    payload = {
        "claims": [c.model_dump(mode="json") for c in out.get("claims") or []],
        "dossier": out["dossier"].model_dump(mode="json") if out.get("dossier") else None,
        "trace": out["trace"].model_dump(mode="json") if out.get("trace") else None,
        "retention": out["retention"].model_dump(mode="json") if out.get("retention") else None,
        "blocked_for_production": out.get("blocked_for_production"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not out.get("blocked_for_production") else 2


if __name__ == "__main__":
    raise SystemExit(main())
