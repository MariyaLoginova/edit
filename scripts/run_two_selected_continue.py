#!/usr/bin/env python3
"""Догнать editorial+F1 для fragility; полный C→F1 для take-home."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.graph import (
    build_editorial_graph,
    build_f1_only_graph,
    build_material_graph,
    build_scenario_graph,
)
from edit.llm import get_chat_model
from edit.search import default_searcher
from models import ClaimCard, Dossier, ScriptDraft


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def editorial_and_f1(dest: Path, dossier: Dossier, script: ScriptDraft, *, llm, searcher) -> None:
    print(f"== {dest.name}: E ==", flush=True)
    ed = build_editorial_graph(llm=llm).invoke({"dossier": dossier, "script": script})
    meta = {
        "blocked_for_production": ed.get("blocked_for_production"),
        "retention_passes": getattr(ed.get("retention"), "passes", None),
        "red_passes": getattr(ed.get("red_critique"), "passes", None),
        "retell_passes": getattr(ed.get("retell"), "passes", None),
        "compression_passes": getattr(ed.get("compression"), "passes", None),
        "dropoff_score": getattr(ed.get("retention"), "dropoff_score", None),
        "summary": getattr(ed.get("retention"), "summary", None),
    }
    dump(dest / "04_editorial_meta.json", meta)
    if ed.get("retention"):
        dump(dest / "04b_retention.json", ed["retention"])
    if ed.get("opening_pick"):
        dump(dest / "04c_openings.json", ed["opening_pick"])
    if ed.get("red_critique"):
        dump(dest / "04d_red.json", ed["red_critique"])
    if ed.get("script"):
        dump(dest / "05_script_edited.json", ed["script"])
    print(meta, flush=True)
    final_script = ed.get("script") or script
    if ed.get("blocked_for_production"):
        print("blocked — skip F1", flush=True)
        return
    print(f"== {dest.name}: F1 ==", flush=True)
    f1 = build_f1_only_graph(searcher=searcher).invoke(
        {"dossier": dossier, "script": final_script}
    )
    dump(dest / "06_shot_list.json", f1["shot_list"])
    print("F1 shots", len(f1["shot_list"].shots), flush=True)


def main() -> int:
    llm = get_chat_model(model="gpt-5-2", temperature=0.0)
    searcher = default_searcher()

    # fragility — resume
    base = Path("runs/goralik-mimimi/selected/cuteness-built-on-fragility")
    dossier = Dossier.model_validate(json.loads((base / "01_dossier.json").read_text()))
    script = ScriptDraft.model_validate(json.loads((base / "03_script.json").read_text()))
    editorial_and_f1(base, dossier, script, llm=llm, searcher=searcher)

    # take-home — full
    claim = ClaimCard.model_validate(
        json.loads(
            Path("runs/goralik-mimimi/selected/claim_pedomorphism-take-home.json").read_text()
        )
    )
    dest = Path("runs/goralik-mimimi/selected") / claim.claim_id
    dest.mkdir(parents=True, exist_ok=True)
    dump(dest / "00_claim.json", claim)
    print("== take-home: C ==", flush=True)
    mat = build_material_graph(llm=llm, searcher=searcher).invoke(
        {"claims": [claim], "selected_claim_id": claim.claim_id}
    )
    dossier = mat["dossier"]
    dump(dest / "01_dossier.json", dossier)
    print("frozen", dossier.frozen, dossier.soft_factcheck, flush=True)
    if not dossier.frozen:
        return 2
    print("== take-home: D ==", flush=True)
    sc = build_scenario_graph(llm=llm).invoke({"dossier": dossier})
    dump(dest / "02_beats.json", sc["beats"])
    dump(dest / "03_script.json", sc["script"])
    print("lines", len(sc["script"].lines), "dur", sc["script"].duration_sec, flush=True)
    editorial_and_f1(dest, dossier, sc["script"], llm=llm, searcher=searcher)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
