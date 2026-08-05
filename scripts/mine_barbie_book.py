#!/usr/bin/env python3
"""A1→A2 по всем главам «Полой женщины»; запускается после восстановления KIE."""

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
    args = p.parse_args()

    llm = get_chat_model(model=args.model, temperature=0.0)
    book_chapters = chapters(SOURCE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    for number in args.chapters:
        text = book_chapters[number - 1]
        source_map = segment_source(
            text,
            source_id=f"barbie-ch{number:02d}",
            title=f"Полая женщина · глава {number}",
            strategy=SegmentStrategy.semantic,
        )
        claims = mine_claims(source_map, llm=llm)
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
        summary.append({"chapter": number, "segments": len(source_map.segments), "claims": len(claims)})
        print(f"глава {number}: {len(claims)} тем")
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
