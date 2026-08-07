#!/usr/bin/env python3
"""Сравнение личного D2: Барби←Лилли в двух методиках (FIX-5)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from edit.c1_material import collect_material
from edit.d2_monologue import write_monologue
from edit.e_check import check_monologue
from edit.e_editor import plan_story
from edit.llm import get_chat_model
from edit.search import SearchHit
from models import ClaimCard, Dossier, SoftFactcheckResult, StoryBrief

load_dotenv(ROOT / ".env")

CLAIM_PATH = ROOT / "runs/goralik-barbie/lilli_steal_like_artist/00_claim.json"
SOURCE_PATH = ROOT / "sources/goralik-barbie-lilli-theft.txt"
OUT = ROOT / "runs/goralik-barbie/lilli-methods-live"
METHODS = ("a_vot_nifiga", "bylo_stalo")


class SourceSearcher:
    def __init__(self, source: str):
        self.source = source

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        return [
            SearchHit(
                url="local://goralik-polaya-zhenshchina/ch03",
                title="Горалик · Полая женщина · глава 3",
                snippet=self.source,
            )
        ]


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    claim = ClaimCard.model_validate_json(CLAIM_PATH.read_text(encoding="utf-8"))
    source = SOURCE_PATH.read_text(encoding="utf-8")
    llm = get_chat_model(model="gpt-5-2", temperature=0.2)
    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT / "00_claim.json", claim)

    draft = collect_material(claim, searcher=SourceSearcher(source), llm=None)
    dossier = draft.model_copy(
        update={
            "material_notes": source,
            "soft_factcheck": SoftFactcheckResult(
                ok=True,
                rationale="Первичный фрагмент книги; E-проверка сверяет монолог с ним.",
            ),
        }
    ).freeze(require_images=False)
    dump(OUT / "01_dossier.json", dossier)

    brief = plan_story(claim, llm=llm)
    dump(OUT / "02_editor_brief.json", brief)
    results = []
    for method in METHODS:
        selected = StoryBrief(
            claim_id=brief.claim_id,
            main_thought=brief.main_thought,
            angle=brief.angle,
            why_viewer=brief.why_viewer,
            visual_evidence=brief.visual_evidence,
            recommended_method=method,
            alternative_methods=[m for m in METHODS if m != method],
            hook_trigger=brief.hook_trigger,
            opening=brief.opening,
            audience_reason=brief.audience_reason,
            share_reason=brief.share_reason,
            proof_plan=brief.proof_plan,
            idea_pitch=brief.idea_pitch,
            needs_external_research=brief.needs_external_research,
            ending_type=brief.ending_type,
        )
        monologue = write_monologue(dossier, selected, llm=llm)
        check = check_monologue(monologue, dossier, llm=llm)
        dump(OUT / f"03_{method}_monologue.json", monologue)
        dump(OUT / f"04_{method}_check.json", check)
        results.append(
            {
                "method": method,
                "passes": check.passes,
                "words": monologue.word_count,
                "text": monologue.text,
                "summary": check.summary,
            }
        )
        print(f"== {method}: passes={check.passes}, words={monologue.word_count} ==")
        print(monologue.text)
    dump(OUT / "05_comparison.json", results)
    return 0 if all(item["passes"] for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
