#!/usr/bin/env python3
"""A1→A2(+B1) по главам «Полой женщины»; запускается после восстановления KIE.

Первый проход уже отдаёт не только темы, но и оценку привлекательности
(пересылка / необычный факт), если не передан --no-score.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.a1_segment import segment_source
from edit.a2_claim_miner import mine_claims
from edit.b1_topic_scoring import append_topic_bank, score_mined_claims
from edit.llm import get_chat_model
from models import SegmentStrategy

SOURCE = ROOT / "sources/goralik-polaya-zhenshchina.txt"
OUT = ROOT / "runs/goralik-barbie/book-a2"
CHAPTER_RE = re.compile(
    r"^\s*Глава\s+(?:первая|вторая|третья|четвертая|пятая|шестая|седьмая|"
    r"восьмая|девятая|десятая|одиннадцатая|двенадцатая|тринадцатая|"
    r"пятнадцатая|шестнадцатая|семнадцатая|14)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def chapters(text: str) -> list[str]:
    matches = list(CHAPTER_RE.finditer(text))[:17]  # затем начинается оглавление
    result = []
    for i, start in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else text.find(
            "\nСодержание", start.end()
        )
        result.append(text[start.start() : end if end > 0 else len(text)])
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chapters", nargs="*", type=int, default=list(range(1, 18)))
    p.add_argument("--model", default="gpt-5-2")
    p.add_argument(
        "--score-model",
        default=None,
        help="Модель для B1 (по умолчанию та же, что --model)",
    )
    p.add_argument(
        "--no-score",
        action="store_true",
        help="Только A2 без пакетного скоринга привлекательности",
    )
    p.add_argument(
        "--format",
        default="narrative",
        choices=["excursion", "narrative", "argument"],
    )
    args = p.parse_args()

    llm = get_chat_model(model=args.model, temperature=0.0)
    score_llm = (
        None
        if args.no_score
        else get_chat_model(model=args.score_model or args.model, temperature=0.0)
    )
    book_chapters = chapters(SOURCE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    all_claims = []
    for number in args.chapters:
        text = book_chapters[number - 1]
        source_map = segment_source(
            text,
            source_id=f"barbie-ch{number:02d}",
            title=f"Полая женщина · глава {number}",
            strategy=SegmentStrategy.semantic,
        )
        claims = mine_claims(source_map, llm=llm)
        all_claims.extend(claims)
        dest = OUT / f"ch{number:02d}.json"
        dest.write_text(
            json.dumps(
                {
                    "chapter": number,
                    "segments": len(source_map.segments),
                    "claims": [c.model_dump(mode="json") for c in claims],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        summary.append(
            {
                "chapter": number,
                "segments": len(source_map.segments),
                "claims": len(claims),
            }
        )
        print(f"глава {number}: {len(claims)} тем")

    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if score_llm is not None and all_claims:
        scored = score_mined_claims(all_claims, format=args.format, llm=score_llm)
        scored_path = OUT / "scored-topics.json"
        scored_path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in scored],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        append_topic_bank(OUT / "topic-bank.md", scored)
        produce = [item for item in scored if item.verdict == "produce"]
        print(
            f"B1: {len(scored)} тем → produce={len(produce)} "
            f"bank={sum(1 for x in scored if x.verdict == 'bank')} "
            f"drop={sum(1 for x in scored if x.verdict == 'drop')}"
        )
        for item in scored[:12]:
            print(f"  {item.verdict:7} {item.total:5.3f}  {item.topic_id} — {item.one_line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
