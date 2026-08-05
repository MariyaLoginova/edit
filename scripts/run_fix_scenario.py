#!/usr/bin/env python3
"""Прогон C→D→F1 после FIX: сценарий VO + описания кадров (поиск-заглушка).

Картинки не курируются: FakeSearcher отдаёт описательные хиты под запрос
(как если бы пришли из стока/архива), чтобы gate пропустил freeze и D/F1
собрали сценарий с визуальными подсказками.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from edit.graph import build_f1_only_graph, build_material_graph, build_scenario_graph
from edit.llm import get_chat_model
from edit.search import SearchHit
from models import ClaimCard
from tests.fakes import FakeSearcher

load_dotenv()


class QueryEchoSearcher(FakeSearcher):
    """Поиск-заглушка: title/snippet = описательный хит под сам запрос."""

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        if self.web:
            return super().search(query, max_results=max_results)
        q = query.strip()
        return [
            SearchHit(
                url=f"https://archive.example/web/{i}",
                title=f"Заметка / эссе · {q[:80]}",
                snippet=q[:200],
            )
            for i in range(max_results)
        ]

    def search_images(self, query: str, *, max_results: int = 8) -> list[SearchHit]:
        q = query.strip()
        slug = re.sub(r"[^\w]+", "-", q.lower())[:40].strip("-") or "img"
        variants = [
            f"сток / архив: {q}",
            f"кадр: {q} · крупный план",
            f"кадр: {q} · средний план, дневной свет",
            f"референс: {q} (музей / печать / реклама)",
            f"вариант: {q} · чуть другой ракурс",
        ]
        return [
            SearchHit(
                url=f"https://img.example/{slug}-{i}.jpg",
                title=variants[i % len(variants)],
                snippet=f"Описание кандидата под запрос «{q}». Отбор и права — на монтаже.",
            )
            for i in range(max_results)
        ]


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    else:
        data = obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _screen_for_role(role: str, claim: ClaimCard, dossier) -> str:
    """Примерное описание кадра из полей карточки + кандидатов C2 (не курация)."""
    a = claim.contrast_pair.state_a
    b = claim.contrast_pair.state_b
    imgs = dossier.image_candidates
    a_hit = imgs.for_state_a[0].title if imgs.for_state_a else f"сток/архив: {a}"
    b_hit = imgs.for_state_b[0].title if imgs.for_state_b else f"сток/архив: {b}"
    mapping = {
        "hook_evidence": f"Крупно: {claim.object_anchor}. Кандидат: {a_hit}",
        "false_explanation": f"Тот же объект в «ожидаемом» чтении. Кандидат: {a_hit}",
        "contrast_ab": f"A → B одного объекта: «{a}» → «{b}». Кандидаты: {a_hit} / {b_hit}",
        "mechanism": f"Держать B на экране, пока называем признаки. Кандидат: {b_hit}",
        "coda": f"Короткий revisit A vs B. Кандидаты: {a_hit} / {b_hit}",
    }
    return mapping.get(role, f"Кадр: {claim.object_anchor}")


def _scenario_md(claim: ClaimCard, script, shot_list, dossier) -> str:
    lines = [
        f"# Сценарий · `{claim.claim_id}`",
        "",
        f"**Объект:** {claim.object_anchor}",
        f"**A/B:** {claim.contrast_pair.state_a} → {claim.contrast_pair.state_b}",
        f"**Механизм:** {claim.mechanism_term}",
        f"**Длительность:** {script.duration_sec:.0f}с",
        "",
        "> Картинки не курировались: колонка «экран» — что искать в стоке/архиве "
        "(из `contrast_pair` + C2-кандидаты). Отбор и права — на монтаже.",
        "",
        "| сек | озвучка | экран (примерно) |",
        "|---|---|---|",
    ]
    n = len(script.lines)
    for i, line in enumerate(script.lines):
        if i == 0:
            role = "hook_evidence"
        elif i == n - 1:
            role = "coda"
        elif i == 1:
            role = "false_explanation"
        elif i >= n - 2:
            role = "mechanism"
        else:
            role = "contrast_ab"
        vis = _screen_for_role(role, claim, dossier)
        text = line.text.replace("|", "\\|").replace("\n", " ")
        vis = vis.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {line.t_start:.0f}–{line.t_end:.0f} | {text} | {vis} |"
        )

    lines.extend(["", "## Claim", "", claim.claim, ""])
    return "\n".join(lines)


def run_one(claim: ClaimCard, out_dir: Path, *, model: str) -> int:
    llm = get_chat_model(model=model, temperature=0.0)
    # web snippet включает цитату — мягкий фактчек чаще проходит
    searcher = QueryEchoSearcher(
        web=[
            SearchHit(
                url="https://archive.example/source",
                title="Источник · визуальная культура / мимими",
                snippet=claim.citation.quote,
            )
        ]
    )
    dest = out_dir / claim.claim_id
    dest.mkdir(parents=True, exist_ok=True)
    _dump(dest / "00_claim.json", claim)

    print(f"== {claim.claim_id}: C1–C3 ==")
    mat = build_material_graph(llm=llm, searcher=searcher).invoke(
        {"claims": [claim], "selected_claim_id": claim.claim_id}
    )
    dossier = mat.get("dossier")
    _dump(dest / "01_dossier.json", dossier)
    if dossier is None or not dossier.frozen:
        blockers = getattr(dossier, "freeze_blockers", None) if dossier else None
        soft = getattr(dossier, "soft_factcheck", None) if dossier else None
        print(f"  BLOCKED freeze blockers={blockers} soft={soft}")
        return 2
    print(
        f"  frozen; images a={len(dossier.image_candidates.for_state_a)} "
        f"b={len(dossier.image_candidates.for_state_b)}"
    )

    print(f"== {claim.claim_id}: D2 ==")
    sc = build_scenario_graph(llm=llm).invoke({"dossier": dossier})
    script = sc["script"]
    _dump(dest / "03_script.json", script)
    print(f"  lines={len(script.lines)} duration={script.duration_sec}s")

    print(f"== {claim.claim_id}: F1 ==")
    f1 = build_f1_only_graph(searcher=searcher).invoke(
        {"dossier": dossier, "script": script}
    )
    shot_list = f1["shot_list"]
    _dump(dest / "06_shot_list.json", shot_list)

    md = _scenario_md(claim, script, shot_list, dossier)
    (dest / "SCENARIO.md").write_text(md, encoding="utf-8")
    print(f"  wrote {dest / 'SCENARIO.md'}")
    print(md)
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--from-fix1",
        type=Path,
        default=ROOT / "runs/goralik-mimimi/fix1_a2_narrow.json",
    )
    p.add_argument(
        "--ids",
        nargs="+",
        default=[
            "cats-crowd-predator-threshold",
            "cake-candy-face-destruction",
        ],
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "runs/goralik-mimimi/fix_scenarios",
    )
    p.add_argument("--model", default="gpt-5-2")
    args = p.parse_args()

    payload = json.loads(args.from_fix1.read_text(encoding="utf-8"))
    by_id = {c["claim_id"]: c for c in payload["claims"]}
    codes = []
    for cid in args.ids:
        if cid not in by_id:
            print(f"нет карточки {cid}", file=sys.stderr)
            codes.append(2)
            continue
        claim = ClaimCard.model_validate(by_id[cid])
        codes.append(run_one(claim, args.out, model=args.model))
    return 0 if all(c == 0 for c in codes) else 2


if __name__ == "__main__":
    raise SystemExit(main())
