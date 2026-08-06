#!/usr/bin/env python3
"""Живой C1→C3→D2→E1→E-критик→E4 прогон темы Barbie safe trend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from edit.c1_material import collect_material
from edit.c3_soft_factcheck import soft_factcheck
from edit.d2_prose import write_prose
from edit.graph import build_e1_only_graph, build_editorial_graph
from edit.llm import get_chat_model
from edit.search import SearchHit
from models import ClaimCard

load_dotenv(ROOT / ".env")

THEMES = ROOT / "runs/goralik-barbie/test-themes.json"
PRIMARY = ROOT / "sources/goralik-barbie-safe-trend.txt"
OUT = ROOT / "runs/goralik-barbie/safe-trend-live"


class SourceSearcher:
    """C1 получает только первичный фрагмент книги, не неподтверждённый веб-шум."""

    def __init__(self, source: str) -> None:
        self.source = source

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        return [
            SearchHit(
                url="local://goralik-polaya-zhenshchina/ch07",
                title="Горалик · Полая женщина · глава 7",
                snippet=self.source,
            )
        ]


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    payload = json.loads(THEMES.read_text(encoding="utf-8"))
    claim = ClaimCard.model_validate(
        next(c for c in payload["claims"] if c["claim_id"] == "barbie-safe-trend-stamp")
    )
    primary = PRIMARY.read_text(encoding="utf-8")
    llm = get_chat_model(model="gpt-5-2", temperature=0.0)
    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT / "00_claim.json", claim)

    print("== C1 ==")
    draft = collect_material(claim, searcher=SourceSearcher(primary), llm=llm)
    # D2/C3 получают первичный текст целиком, не только LLM-выжимку C1.
    draft = draft.model_copy(
        update={
            "material_notes": (
                f"{draft.material_notes}\n\nПЕРВИЧНЫЙ ФРАГМЕНТ КНИГИ:\n{primary}"
            )
        }
    )
    dump(OUT / "01_material_draft.json", draft)

    print("== C3 ==")
    dossier = soft_factcheck(draft, llm=llm, auto_freeze=True)
    dump(OUT / "02_dossier.json", dossier)
    print("  frozen:", dossier.frozen, "blockers:", dossier.freeze_blockers)
    if not dossier.frozen:
        return 2

    print("== D2 ==")
    script = write_prose(dossier, llm=llm)
    dump(OUT / "03_script.json", script)
    for line in script.lines:
        print(f"  {line.t_start:.0f}–{line.t_end:.0f}: {line.text}")

    print("== E1 ==")
    e1 = build_e1_only_graph().invoke({"dossier": dossier, "script": script})
    dump(OUT / "04_trace.json", e1["trace"])
    print("  passes:", e1["trace"].passes)
    if not e1["trace"].passes:
        return 2

    print("== E-критик → E4 ==")
    ed = build_editorial_graph(llm=llm).invoke({"dossier": dossier, "script": script})
    dump(OUT / "04b_critique.json", ed.get("critique"))
    dump(OUT / "04c_openings.json", ed.get("opening_pick"))
    dump(OUT / "05_script_edited.json", ed.get("script"))
    meta = {
        "blocked_for_production": ed.get("blocked_for_production"),
        "critique_passes": ed["critique"].passes if ed.get("critique") else None,
        "dropoff_score": ed["critique"].dropoff_score if ed.get("critique") else None,
        "retell": ed["critique"].retell if ed.get("critique") else None,
        "virality_factors": ed["critique"].virality_factors if ed.get("critique") else [],
        "missing_evidence": ed["critique"].missing_evidence if ed.get("critique") else [],
        "provocation": ed["critique"].provocation if ed.get("critique") else "",
        "opening": ed["opening_pick"].chosen_text if ed.get("opening_pick") else None,
    }
    dump(OUT / "04_editorial_meta.json", meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0 if not meta["blocked_for_production"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
