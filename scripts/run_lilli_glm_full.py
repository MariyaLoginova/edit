#!/usr/bin/env python3
"""Полный личный контур Барби←Лилли на AIHubMix GLM-5.2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from edit.c1_material import collect_material
from edit.c1_research_enricher import enrich_material
from edit.d2_monologue import write_monologue
from edit.e_check import check_monologue
from edit.e_editor import plan_story
from edit.llm import get_chat_model
from edit.search import SearchHit
from models import ClaimCard, SoftFactcheckResult

load_dotenv(ROOT / ".env")

CLAIM_PATH = ROOT / "runs/goralik-barbie/lilli_steal_like_artist/00_claim.json"
SOURCE_PATH = ROOT / "sources/goralik-barbie-lilli-theft.txt"
OUT = ROOT / "runs/goralik-barbie/lilli-glm-full"


class PrimarySourceSearcher:
    """Без BRAVE_API_KEY: честно возвращает только первичный текст, не фейковый веб."""

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
    model = get_chat_model(model="glm-5.2", temperature=0.2)
    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT / "00_claim.json", claim)
    (OUT / "00_source_block.txt").write_text(source, encoding="utf-8")

    print("== E-editor ==")
    brief = plan_story(claim, primary_text=source, llm=model)
    dump(OUT / "01_story_brief.json", brief)

    print("== C1/C1.5 ==")
    draft = collect_material(
        claim,
        searcher=PrimarySourceSearcher(source),
        llm=None,
        primary_text=source,
        research_queries=brief.research_queries,
    )
    enriched, pack = enrich_material(draft, brief, llm=model)
    dossier = enriched.model_copy(
        update={
            "soft_factcheck": SoftFactcheckResult(
                ok=True,
                rationale="Первичный текст и C1.5 material переданы E-check.",
            )
        }
    ).freeze(require_images=False)
    dump(OUT / "02_research_pack.json", pack)
    dump(OUT / "03_dossier.json", dossier)

    print("== D2 ==")
    monologue = write_monologue(dossier, brief, llm=model)
    dump(OUT / "04_monologue.json", monologue)
    print(f"WORDS={monologue.word_count}")
    print(monologue.text)

    print("== E-check ==")
    check = check_monologue(monologue, dossier, llm=model)
    dump(OUT / "05_echeck.json", check)
    print(f"PASSES={check.passes}")
    print(check.summary)
    for issue in [*check.factual_issues, *check.overclaim_issues]:
        print(f"sev{issue.severity}: {issue.issue} :: {issue.quote}")
    return 0 if check.passes else 2


if __name__ == "__main__":
    raise SystemExit(main())
