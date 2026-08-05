#!/usr/bin/env python3
"""Прогоны EDIT: A2 / C / D / E / F / G / срезы вех 1–5."""

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
    build_editorial_graph,
    build_f1_only_graph,
    build_learning_graph,
    build_material_graph,
    build_scenario_graph,
    build_v2_slice_graph,
    build_v3_slice_graph,
    build_v4_slice_graph,
    build_v5_slice_graph,
    build_vertical_slice_graph,
)
from models import ClaimCard, Dossier, RolloutMetrics, ScriptDraft, SourceMap


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
    p_e1.add_argument("dossier", type=Path)

    p_mat = sub.add_parser("material", help="C1→C2→C3(+freeze)")
    p_mat.add_argument("--claim-json", type=Path, required=True)

    p_sc = sub.add_parser("scenario", help="D1→D2→D3 из frozen dossier JSON")
    p_sc.add_argument("dossier", type=Path)

    p_v1 = sub.add_parser("slice", help="Веха 1: A2→B2→E2")
    p_v1.add_argument("--source", type=Path, required=True)
    p_v1.add_argument("--script", type=Path, required=True)
    p_v1.add_argument("--claim-id", default=None)

    p_v2 = sub.add_parser("v2", help="Веха 2: A2→C→D-stub→E1→E2")
    p_v2.add_argument("--source", type=Path, required=True)
    p_v2.add_argument("--script", type=Path, required=True)
    p_v2.add_argument("--claim-id", default=None)

    p_v3 = sub.add_parser("v3", help="Веха 3: A2→C→D1–D3→E1→E2")
    p_v3.add_argument("--source", type=Path, required=True)
    p_v3.add_argument("--claim-id", default=None)

    p_ed = sub.add_parser("editorial", help="E2→E6 на готовых script+dossier")
    p_ed.add_argument("--script", type=Path, required=True)
    p_ed.add_argument("--dossier", type=Path, required=True)

    p_v4 = sub.add_parser("v4", help="Веха 4: полный срез до E6")
    p_v4.add_argument("--source", type=Path, required=True)
    p_v4.add_argument("--claim-id", default=None)

    p_f1 = sub.add_parser("f1", help="Раскадровка ShotList")
    p_f1.add_argument("--script", type=Path, required=True)
    p_f1.add_argument("--dossier", type=Path, required=True)

    p_g1 = sub.add_parser("learn", help="G1: метрики → веса B1 / порог E2")
    p_g1.add_argument("metrics_json", type=Path, help="JSON list[RolloutMetrics]")
    p_g1.add_argument("--persist", action="store_true", help="Записать config/thresholds.yaml")

    p_v5 = sub.add_parser("v5", help="Веха 5: полный срез до F1")
    p_v5.add_argument("--source", type=Path, required=True)
    p_v5.add_argument("--claim-id", default=None)

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

    if args.cmd == "scenario":
        dossier = Dossier.model_validate(_load_json(args.dossier))
        out = build_scenario_graph().invoke({"dossier": dossier})
        payload = {
            "beats": out["beats"].model_dump(mode="json"),
            "script": out["script"].model_dump(mode="json"),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

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

    if args.cmd == "v2":
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

    if args.cmd == "v3":
        source = SourceMap.model_validate(_load_json(args.source))
        out = build_v3_slice_graph().invoke(
            {"source_map": source, "selected_claim_id": args.claim_id}
        )
        payload = {
            "claims": [c.model_dump(mode="json") for c in out.get("claims") or []],
            "dossier": out["dossier"].model_dump(mode="json") if out.get("dossier") else None,
            "beats": out["beats"].model_dump(mode="json") if out.get("beats") else None,
            "script": out["script"].model_dump(mode="json") if out.get("script") else None,
            "trace": out["trace"].model_dump(mode="json") if out.get("trace") else None,
            "retention": out["retention"].model_dump(mode="json") if out.get("retention") else None,
            "blocked_for_production": out.get("blocked_for_production"),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if not out.get("blocked_for_production") else 2

    if args.cmd == "editorial":
        script = ScriptDraft.model_validate(_load_json(args.script))
        dossier = Dossier.model_validate(_load_json(args.dossier))
        out = build_editorial_graph().invoke({"script": script, "dossier": dossier})
        payload = {
            "script": out["script"].model_dump(mode="json") if out.get("script") else None,
            "retention": out["retention"].model_dump(mode="json") if out.get("retention") else None,
            "red_critique": out["red_critique"].model_dump(mode="json") if out.get("red_critique") else None,
            "opening_pick": {
                "chosen_index": out["opening_pick"].chosen_index,
                "chosen_text": out["opening_pick"].chosen_text,
                "variants": [v.model_dump(mode="json") for v in out["opening_pick"].variants],
            }
            if out.get("opening_pick")
            else None,
            "retell": out["retell"].model_dump(mode="json") if out.get("retell") else None,
            "compression": {
                "reduction_ratio": out["compression"].reduction_ratio,
                "passes": out["compression"].passes,
                "summary": out["compression"].summary,
            }
            if out.get("compression")
            else None,
            "blocked_for_production": out.get("blocked_for_production"),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if not out.get("blocked_for_production") else 2

    if args.cmd == "v4":
        source = SourceMap.model_validate(_load_json(args.source))
        out = build_v4_slice_graph().invoke(
            {"source_map": source, "selected_claim_id": args.claim_id}
        )
        payload = {
            "claims": [c.model_dump(mode="json") for c in out.get("claims") or []],
            "dossier": out["dossier"].model_dump(mode="json") if out.get("dossier") else None,
            "beats": out["beats"].model_dump(mode="json") if out.get("beats") else None,
            "script": out["script"].model_dump(mode="json") if out.get("script") else None,
            "trace": out["trace"].model_dump(mode="json") if out.get("trace") else None,
            "retention": out["retention"].model_dump(mode="json") if out.get("retention") else None,
            "red_critique": out["red_critique"].model_dump(mode="json") if out.get("red_critique") else None,
            "retell": out["retell"].model_dump(mode="json") if out.get("retell") else None,
            "compression": {
                "reduction_ratio": out["compression"].reduction_ratio,
                "passes": out["compression"].passes,
            }
            if out.get("compression")
            else None,
            "blocked_for_production": out.get("blocked_for_production"),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if not out.get("blocked_for_production") else 2

    if args.cmd == "f1":
        script = ScriptDraft.model_validate(_load_json(args.script))
        dossier = Dossier.model_validate(_load_json(args.dossier))
        out = build_f1_only_graph().invoke({"script": script, "dossier": dossier})
        print(json.dumps(out["shot_list"].model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "learn":
        raw = _load_json(args.metrics_json)
        metrics = [RolloutMetrics.model_validate(m) for m in raw]
        out = build_learning_graph(persist=args.persist).invoke({"rollout_metrics": metrics})
        print(json.dumps(out["weight_update"].model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    # v5
    source = SourceMap.model_validate(_load_json(args.source))
    out = build_v5_slice_graph().invoke(
        {"source_map": source, "selected_claim_id": args.claim_id}
    )
    payload = {
        "scored_claims": [
            {
                "claim_id": s.claim.claim_id,
                "total": s.total,
                "rank": s.rank,
                "scores": s.scores,
            }
            for s in (out.get("scored_claims") or [])
        ],
        "dossier": out["dossier"].model_dump(mode="json") if out.get("dossier") else None,
        "script": out["script"].model_dump(mode="json") if out.get("script") else None,
        "shot_list": out["shot_list"].model_dump(mode="json") if out.get("shot_list") else None,
        "blocked_for_production": out.get("blocked_for_production"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not out.get("blocked_for_production") else 2


if __name__ == "__main__":
    raise SystemExit(main())
