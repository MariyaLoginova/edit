#!/usr/bin/env python3
"""После B1: взять лучшую produce-тему Пастуро и прогнать личный контур."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BOOK_A2 = ROOT / "runs/pastoureau-cherny/book-a2"
SOURCE = ROOT / "sources/pastoureau-cherny.txt"
CHAPTERS = BOOK_A2 / "chapters"


def load_scored(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_claim(topic_id: str) -> tuple[dict, Path]:
    book_path = BOOK_A2 / "book-claims.json"
    candidates = [book_path] if book_path.exists() else []
    candidates.extend(sorted(BOOK_A2.glob("ch[0-9]*.json")))
    for path in candidates:
        data = json.loads(path.read_text(encoding="utf-8"))
        for claim in data.get("claims") or []:
            if claim.get("claim_id") == topic_id:
                return claim, path
    raise SystemExit(f"claim не найден в book-a2: {topic_id}")


def chapter_source_for(chapter_json: Path) -> Path:
    if chapter_json.name == "book-claims.json":
        return SOURCE
    slug = chapter_json.stem  # ch01-intro
    candidate = CHAPTERS / f"{slug}.txt"
    if candidate.exists():
        return candidate
    return SOURCE


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="gpt-5-2")
    p.add_argument("--topic-id", default=None, help="иначе берём лучший produce")
    p.add_argument("--rank", type=int, default=1, help="N-я produce-тема (1 = лучшая)")
    p.add_argument("--scored", type=Path, default=BOOK_A2 / "scored-topics.json")
    args = p.parse_args()

    scored = load_scored(args.scored)
    produce = [x for x in scored if x.get("verdict") == "produce"]
    if not produce:
        produce = [x for x in scored if x.get("gates_passed")]
    if not produce:
        raise SystemExit("нет produce/gates_passed тем в scored-topics.json")

    if args.topic_id:
        topic = next((x for x in scored if x.get("topic_id") == args.topic_id), None)
        if topic is None:
            raise SystemExit(f"topic_id не найден: {args.topic_id}")
    else:
        idx = max(1, args.rank) - 1
        if idx >= len(produce):
            raise SystemExit(f"rank={args.rank}, а produce всего {len(produce)}")
        topic = produce[idx]

    topic_id = topic["topic_id"]
    claim, chapter_json = find_claim(topic_id)
    source_path = chapter_source_for(chapter_json)
    out = ROOT / "runs/pastoureau-cherny" / f"produce-{topic_id}"
    claim_path = out / "00_claim.json"
    out.mkdir(parents=True, exist_ok=True)
    claim_path.write_text(json.dumps(claim, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"topic={topic_id} total={topic.get('total')} from={chapter_json.name}")
    print(f"source={source_path}")
    print(f"out={out}")

    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_personal_full_audit.py"),
        "--claim",
        str(claim_path),
        "--source",
        str(source_path),
        "--out",
        str(out),
        "--model",
        args.model,
        "--source-title",
        "Мишель Пастуро · Черный. История цвета",
        "--source-url",
        "local://pastoureau-cherny",
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
