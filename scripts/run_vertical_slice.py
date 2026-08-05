#!/usr/bin/env python3
"""Вертикальный срез вехи 1: A2 на source_map и/или E2 на ручном ScriptDraft.

Примеры:
  python scripts/run_vertical_slice.py a2 tests/fixtures/fashion_theory_segment.json
  python scripts/run_vertical_slice.py e2 tests/fixtures/script_weak.json
  python scripts/run_vertical_slice.py slice \\
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

from edit.graph import build_a2_only_graph, build_e2_only_graph, build_vertical_slice_graph
from models import ScriptDraft, SourceMap


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="EDIT веха 1 — вертикальный срез A2/E2")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_a2 = sub.add_parser("a2", help="Прогнать майнер тезисов")
    p_a2.add_argument("source_map", type=Path)

    p_e2 = sub.add_parser("e2", help="Прогнать критика удержания")
    p_e2.add_argument("script", type=Path)

    p_slice = sub.add_parser("slice", help="A2 → stub B2 → E2")
    p_slice.add_argument("--source", type=Path, required=True)
    p_slice.add_argument("--script", type=Path, required=True)
    p_slice.add_argument("--claim-id", default=None)

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


if __name__ == "__main__":
    raise SystemExit(main())
