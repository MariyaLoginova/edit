#!/usr/bin/env python3
"""Матрица A1→A2: strategy × model → ClaimCard в runs/{source_id}/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.a1_segment import segment_all_strategies
from edit.a2_claim_miner import citation_hit_rate, mine_claims
from edit.kie_client import load_llm_config
from edit.llm import get_chat_model
from models import SegmentStrategy


def _safe_model_slug(model: str) -> str:
    return model.replace("/", "-").replace(" ", "_")


def main() -> int:
    p = argparse.ArgumentParser(description="EDIT A1→A2 matrix run")
    p.add_argument("source", type=Path, help="Путь к главе (.txt/.md)")
    p.add_argument("--source-id", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--language", default="ru", choices=["ru", "en"])
    p.add_argument(
        "--strategies",
        nargs="*",
        default=None,
        help="Подмножество стратегий (по умолчанию из config)",
    )
    p.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Подмножество моделей (по умолчанию из config a1_a2_matrix.models)",
    )
    p.add_argument(
        "--a1-only",
        action="store_true",
        help="Только сегментация → source_map JSON, без A2/KIE",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "runs",
        help="Корень для артефактов (default: runs/)",
    )
    args = p.parse_args()

    if not args.source.is_file():
        print(f"нет файла: {args.source}", file=sys.stderr)
        return 2

    cfg = load_llm_config()
    matrix = cfg.get("a1_a2_matrix") or {}
    strategies = args.strategies or matrix.get("strategies") or [s.value for s in SegmentStrategy]
    models = args.models or matrix.get("models") or [cfg.get("default_model")]

    source_id = args.source_id or args.source.stem
    title = args.title or args.source.stem
    text = args.source.read_text(encoding="utf-8")
    out_dir = args.out / source_id
    out_dir.mkdir(parents=True, exist_ok=True)

    maps = segment_all_strategies(
        text, source_id=source_id, title=title, language=args.language
    )
    # сохранить все source_map
    for strat, smap in maps.items():
        path = out_dir / f"source_map_{strat.value}.json"
        path.write_text(
            json.dumps(smap.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"A1 {strat.value}: {len(smap.segments)} segments → {path}")

    if args.a1_only:
        return 0

    summary_rows: list[dict] = []
    for strat_name in strategies:
        strat = SegmentStrategy(strat_name)
        smap = maps[strat]
        for model_id in models:
            slug = _safe_model_slug(model_id)
            out_path = out_dir / f"{strat.value}_{slug}.json"
            print(f"A2 {strat.value} × {model_id} …", flush=True)
            llm = get_chat_model(model=model_id, temperature=0.0)
            # один прогон без фильтра цитат → считаем hit-rate, потом принимаем только hits
            raw_cards = mine_claims(
                smap, llm=llm, model=model_id, require_quote_substring=False
            )
            rate_info = citation_hit_rate(raw_cards, smap)
            by_id = {s.segment_id: s for s in smap.segments}
            accepted = []
            for c in raw_cards:
                seg = by_id.get(c.source_segment_id)
                if seg is None:
                    continue
                norm_q = " ".join(c.citation.quote.split())
                norm_t = " ".join(seg.text.split())
                if norm_q and norm_q in norm_t:
                    accepted.append(c)
            payload = {
                "source_id": source_id,
                "strategy": strat.value,
                "model": model_id,
                "segment_count": len(smap.segments),
                "citation_check": rate_info,
                "cards": [c.model_dump(mode="json") for c in accepted],
                "cards_raw_unfiltered": [c.model_dump(mode="json") for c in raw_cards],
            }
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            row = {
                "strategy": strat.value,
                "model": model_id,
                "segments": len(smap.segments),
                "cards_accepted": len(accepted),
                "cards_raw": len(raw_cards),
                "citation_rate": rate_info["rate"],
                "path": str(out_path.relative_to(ROOT)),
            }
            summary_rows.append(row)
            print(
                f"  → {len(accepted)} cards (raw={len(raw_cards)}, "
                f"citation_rate={rate_info['rate']:.0%}) {out_path}"
            )

    summary_path = out_dir / "matrix_summary.json"
    summary_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"summary → {summary_path}")
    notes = out_dir / "NOTES.md"
    if not notes.exists():
        notes.write_text(
            _notes_template(source_id, summary_rows),
            encoding="utf-8",
        )
        print(f"черновик оценки → {notes}")
    return 0


def _notes_template(source_id: str, rows: list[dict]) -> str:
    lines = [
        f"# Ручная оценка A1→A2 · `{source_id}`",
        "",
        "Смотреть: причинность / разрыв ожидания / visual_hint / цитата / тишина на биографии.",
        "",
        "## Матрица (авто)",
        "",
        "| strategy | model | segments | accepted | citation_rate |",
        "|---|---|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['strategy']} | {r['model']} | {r['segments']} | "
            f"{r['cards_accepted']} | {r['citation_rate']:.0%} |"
        )
    lines += [
        "",
        "## Выводы (заполнить глазами)",
        "",
        "### Какая стратегия даёт цельные тезисы?",
        "",
        "- paragraph: …",
        "- semantic: …",
        "- fixed_window: …",
        "",
        "**Стратегия по умолчанию:** … (обоснование)",
        "",
        "### Какая модель держит причинность и цитаты?",
        "",
        "- …",
        "",
        "### Сигнал по гипотезе «причинный тезис из книги»",
        "",
        "- жива / промпт A2 переделывать: …",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
