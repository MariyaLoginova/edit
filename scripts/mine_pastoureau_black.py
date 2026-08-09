#!/usr/bin/env python3
"""A1→A2→B1 по книге Мишеля Пастуро «Черный. История цвета».

Первый проход: главы → темы + оценка привлекательности (пересылка / факт).
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

UPLOAD = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/"
    "Mishel_Pasturo_Cherny_Istoria_tsveta_3e43.txt"
)
SOURCE = ROOT / "sources/pastoureau-cherny.txt"
OUT = ROOT / "runs/pastoureau-cherny/book-a2"

# Заголовки тела книги (порядок чтения). Часть OCR-заголовков разбита на 2 строки.
CHAPTERS: list[tuple[str, str]] = [
    ("intro", r"Введение\.\s+Цвет в зеркале истории"),
    ("mythology-darkness", r"Мифология тьмы"),
    ("darkness-to-color", r"От мрака к многоцветью"),
    ("palette-to-lexicon", r"От палитры к словарю"),
    ("death-color", r"Смерть и ее цвет"),
    ("black-bird", r"Черная птица"),
    ("black-white-red", r"Черный,\s*белый,\s*красный"),
    ("devil-images", r"Дьявол и его изображения"),
    ("devil-colors", r"Дьявол и его цвета"),
    ("bestiary", r"Зловещий бестиарий"),
    ("dispel-darkness", r"Разогнать тьму"),
    ("monks-quarrel", r"Война монахов:\s*(?:\n\s*)?белое против черного"),
    ("heraldry", r"Новый цветовой порядок:\s*(?:\n\s*)?геральдика"),
    ("black-knight", r"Черный рыцарь:\s*кто он\?"),
    ("skin-colors", r"Цвета кожи"),
    ("christianization", r"Христианизация темнокожих"),
    ("christ-dyer", r"Христос у красильщика"),
    ("dyeing-black", r"Окрашивание в черное"),
    ("color-morality", r"Цвет и мораль"),
    ("princely-luxury", r"Роскошь венценосцев"),
    ("gray-hope", r"Серый цвет надежды"),
    ("ink-paper", r"Краска и бумага"),
    ("bw-coloring", r"Черно-белый колорит"),
    ("hachures", r"Точки и штрихи"),
    ("protestant-dress", r"Протестантская одежда"),
    ("somber-century", r"Очень темный век"),
    ("devil-return", r"Возвращение Дьявола"),
    ("new-classifications", r"Новые спекуляции,\s*новые классификации"),
    # не путать с «Новый цветовой порядок: геральдика»
    ("new-color-order", r"Новый цветовой порядок(?!\s*:)"),
    ("triumph-color", r"Триумф цвета"),
    ("enlightenment", r"Век Просвещения"),
    ("melancholy", r"Поэзия меланхолии"),
    ("coal-factories", r"Время угля и заводов"),
    ("images-world", r"Что происходит\s*(?:\n\s*)?в мире изображений"),
    ("modern-color", r"Актуальный цвет"),
    ("dangerous-color", r"Опасный цвет\?"),
]

NOTES_MARKERS = (
    "Примечания",
    "Библиография",
    "Благодарности",
)


def clean_ocr(text: str) -> str:
    text = text.replace("\x0c", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Убрать колонтитулы вида «Смерть и ее цвет   27»
    text = re.sub(
        r"(?m)^[ \t]*([А-ЯЁа-яё][^\n]{0,60}?)[ \t]{2,}\d{1,3}[ \t]*$",
        "",
        text,
    )
    # Склеить переносы: сло-\nво → слово
    text = re.sub(r"([а-яёА-ЯЁ])-\n([а-яё])", r"\1\2", text)
    # Сжать пробелы внутри строк, сохранить абзацы
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def ensure_source(*, force: bool = False) -> str:
    if SOURCE.exists() and not force:
        return SOURCE.read_text(encoding="utf-8")
    raw = UPLOAD.read_text(encoding="utf-8", errors="replace")
    cleaned = clean_ocr(raw)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text(cleaned, encoding="utf-8")
    return cleaned


def find_chapters(text: str) -> list[tuple[str, str, int, int]]:
    """→ (slug, title, start, end). Берём первое вхождение после оглавления."""
    starts: list[tuple[str, str, int]] = []
    for slug, pattern in CHAPTERS:
        rx = re.compile(pattern)
        hits = list(rx.finditer(text))
        body = [h for h in hits if h.start() > 12000]
        hit = body[0] if body else (hits[-1] if hits and slug == "intro" else None)
        if hit is None:
            print(f"WARN: не найден раздел {slug}")
            continue
        title = re.sub(r"\s+", " ", hit.group(0)).strip()
        starts.append((slug, title, hit.start()))
    starts.sort(key=lambda x: x[2])

    # Обрезать примечания / библиографию (колонтитулы OCR: «138 Примечания»)
    end_limit = len(text)
    for rx in (
        r"(?m)^\d{0,3}\s*Примечания\s*$",
        r"(?m)^Библиография\s*$",
    ):
        for m in re.finditer(rx, text):
            if m.start() > 300000:
                end_limit = min(end_limit, m.start())
                break

    out: list[tuple[str, str, int, int]] = []
    for i, (slug, title, start) in enumerate(starts):
        end = starts[i + 1][2] if i + 1 < len(starts) else end_limit
        if end <= start:
            continue
        out.append((slug, title, start, end))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chapters", nargs="*", default=None, help="slug'и разделов")
    p.add_argument("--model", default="gpt-5-2")
    p.add_argument("--score-model", default=None)
    p.add_argument("--no-score", action="store_true")
    p.add_argument("--force-source", action="store_true")
    p.add_argument("--resume", action="store_true", help="не переписывать готовые ch-*.json")
    p.add_argument("--format", default="narrative", choices=["excursion", "narrative", "argument"])
    p.add_argument("--limit", type=int, default=0, help="макс. число глав (0 = все)")
    args = p.parse_args()

    text = ensure_source(force=args.force_source)
    chapters = find_chapters(text)
    if args.chapters:
        wanted = set(args.chapters)
        chapters = [c for c in chapters if c[0] in wanted]
    if args.limit:
        chapters = chapters[: args.limit]

    OUT.mkdir(parents=True, exist_ok=True)
    chapters_dir = OUT / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    (OUT / "chapters_index.json").write_text(
        json.dumps(
            [
                {
                    "slug": slug,
                    "title": title,
                    "start": start,
                    "end": end,
                    "chars": end - start,
                }
                for slug, title, start, end in chapters
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    llm = get_chat_model(model=args.model, temperature=0.0)
    summary = []
    all_claims = []

    for n, (slug, title, start, end) in enumerate(chapters, start=1):
        dest = OUT / f"ch{n:02d}-{slug}.json"
        chapter_text = text[start:end].strip()
        (chapters_dir / f"ch{n:02d}-{slug}.txt").write_text(chapter_text + "\n", encoding="utf-8")

        if args.resume and dest.exists():
            data = json.loads(dest.read_text(encoding="utf-8"))
            from models import ClaimCard

            claims = [ClaimCard.model_validate(c) for c in data.get("claims") or []]
            all_claims.extend(claims)
            summary.append(
                {
                    "n": n,
                    "slug": slug,
                    "title": title,
                    "segments": data.get("segments"),
                    "claims": len(claims),
                    "resumed": True,
                }
            )
            print(f"[{n}/{len(chapters)}] resume {slug}: {len(claims)} тем")
            continue

        print(f"[{n}/{len(chapters)}] A1/A2 {slug} ({len(chapter_text)} chars) …")
        source_map = segment_source(
            chapter_text,
            source_id=f"pastoureau-{slug}",
            title=f"Пастуро · {title}",
            strategy=SegmentStrategy.semantic,
        )
        claims = mine_claims(source_map, llm=llm)
        all_claims.extend(claims)
        dest.write_text(
            json.dumps(
                {
                    "n": n,
                    "slug": slug,
                    "title": title,
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
                "n": n,
                "slug": slug,
                "title": title,
                "segments": len(source_map.segments),
                "claims": len(claims),
                "resumed": False,
            }
        )
        print(f"  → {len(claims)} тем / {len(source_map.segments)} сегм.")

    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not args.no_score and all_claims:
        score_llm = get_chat_model(model=args.score_model or args.model, temperature=0.0)
        print(f"B1: скоринг {len(all_claims)} тем …")
        scored = score_mined_claims(all_claims, format=args.format, llm=score_llm)
        (OUT / "scored-topics.json").write_text(
            json.dumps([s.model_dump(mode="json") for s in scored], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        append_topic_bank(OUT / "topic-bank.md", scored)

        lines = [
            "# Пастуро · Черный · shortlist B1",
            "",
            f"Модель A2/B1: `{args.model}` / `{args.score_model or args.model}`",
            f"Тем: {len(scored)}",
            "",
            "| verdict | total | topic_id | one_line |",
            "|---|---:|---|---|",
        ]
        for item in scored:
            safe = item.one_line.replace("|", "\\|")
            lines.append(
                f"| {item.verdict} | {item.total:.3f} | `{item.topic_id}` | {safe} |"
            )
        (OUT / "THEME_SHORTLIST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

        produce = [x for x in scored if x.verdict == "produce"]
        print(
            f"B1 done: produce={len(produce)} "
            f"bank={sum(1 for x in scored if x.verdict == 'bank')} "
            f"drop={sum(1 for x in scored if x.verdict == 'drop')}"
        )
        for item in scored[:15]:
            print(f"  {item.verdict:7} {item.total:5.3f}  {item.topic_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
