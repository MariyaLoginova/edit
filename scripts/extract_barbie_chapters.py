#!/usr/bin/env python3
"""Механически выделяет 17 глав «Полой женщины» в отдельные source-файлы."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/goralik-polaya-zhenshchina.txt"
OUT = ROOT / "sources/goralik-barbie-chapters"

CHAPTER_RE = re.compile(
    r"^\s*Глава\s+(?:первая|вторая|третья|четвертая|пятая|шестая|седьмая|"
    r"восьмая|девятая|десятая|одиннадцатая|двенадцатая|тринадцатая|"
    r"пятнадцатая|шестнадцатая|семнадцатая|14)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _clean(text: str) -> str:
    text = re.sub(r"\n\s*\d{1,3}\s*\n", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip() + "\n"


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    matches = list(CHAPTER_RE.finditer(text))[:17]  # дальше идёт оглавление
    if len(matches) != 17:
        raise RuntimeError(f"ожидалось 17 глав, найдено {len(matches)}")

    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for i, match in enumerate(matches, start=1):
        end = matches[i].start() if i < len(matches) else text.find("\nСодержание", match.end())
        if end < 0:
            end = len(text)
        chunk = _clean(text[match.start() : end])
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        title = " ".join(lines[:2])
        path = OUT / f"{i:02d}.txt"
        path.write_text(
            f"Источник: Линор Горалик, «Полая женщина» (2005)\n"
            f"Глава {i}\n\n{chunk}",
            encoding="utf-8",
        )
        index.append(
            {
                "chapter": i,
                "title": title,
                "file": path.name,
                "words": len(chunk.split()),
            }
        )

    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
