#!/usr/bin/env python3
"""Прогон выбранных ClaimCard: C → D2 → E1 → E-критик → E4 → F1 (FIX-4)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.graph import (
    build_e1_only_graph,
    build_editorial_graph,
    build_f1_only_graph,
    build_material_graph,
    build_scenario_graph,
)
from edit.llm import get_chat_model
from edit.search import default_searcher
from models import ClaimCard


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    else:
        data = obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_one(claim_path: Path, out_dir: Path, *, model: str) -> int:
    claim = ClaimCard.model_validate(json.loads(claim_path.read_text(encoding="utf-8")))
    llm = get_chat_model(model=model, temperature=0.0)
    searcher = default_searcher()
    stem = claim.claim_id
    dest = out_dir / stem
    dest.mkdir(parents=True, exist_ok=True)
    _dump(dest / "00_claim.json", claim)

    print(f"== {stem}: C1–C3 ==")
    mat = build_material_graph(llm=llm, searcher=searcher).invoke(
        {"claims": [claim], "selected_claim_id": claim.claim_id}
    )
    dossier = mat.get("dossier")
    _dump(dest / "01_dossier.json", dossier)
    if dossier is None or not dossier.frozen:
        print(f"  BLOCKED: dossier not frozen ({dossier and dossier.soft_factcheck})")
        return 2
    imgs = dossier.image_candidates.all_images()
    print(
        f"  frozen ok; images={len(imgs)} "
        f"(a={len(dossier.image_candidates.for_state_a)} "
        f"b={len(dossier.image_candidates.for_state_b)})"
    )

    print(f"== {stem}: D2 ==")
    sc = build_scenario_graph(llm=llm).invoke({"dossier": dossier})
    _dump(dest / "03_script.json", sc["script"])
    print(f"  script lines={len(sc['script'].lines)} duration={sc['script'].duration_sec}s")

    print(f"== {stem}: E1 ==")
    e1 = build_e1_only_graph().invoke({"dossier": dossier, "script": sc["script"]})
    _dump(dest / "04_trace.json", e1.get("trace"))
    if not e1["trace"].passes:
        print("  BLOCKED at E1")
        return 2

    print(f"== {stem}: E-критик → E4 ==")
    ed = build_editorial_graph(llm=llm).invoke(
        {"dossier": dossier, "script": sc["script"]}
    )
    payload = {
        "blocked_for_production": ed.get("blocked_for_production"),
        "trace_passes": True,
        "critique_passes": ed["critique"].passes if ed.get("critique") else None,
        "dropoff_score": ed["critique"].dropoff_score if ed.get("critique") else None,
        "retell": ed["critique"].retell if ed.get("critique") else None,
    }
    _dump(dest / "04_editorial_meta.json", payload)
    if ed.get("critique"):
        _dump(dest / "04b_critique.json", ed["critique"])
    if ed.get("script"):
        _dump(dest / "05_script_edited.json", ed["script"])
    if ed.get("opening_pick"):
        _dump(dest / "04c_openings.json", ed["opening_pick"])
    print("  editorial:", payload)

    if ed.get("blocked_for_production"):
        print("  BLOCKED for production — skip F1")
        return 2

    script = ed.get("script") or sc["script"]
    print(f"== {stem}: F1 ==")
    f1 = build_f1_only_graph(searcher=searcher).invoke(
        {"dossier": dossier, "script": script}
    )
    _dump(dest / "06_shot_list.json", f1["shot_list"])
    print(f"  shots={len(f1['shot_list'].shots)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("claims", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", default="gpt-5-2")
    args = p.parse_args()
    codes = [run_one(c, args.out, model=args.model) for c in args.claims]
    return 0 if all(c == 0 for c in codes) else 2


if __name__ == "__main__":
    raise SystemExit(main())
