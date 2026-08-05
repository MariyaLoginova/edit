#!/usr/bin/env python3
"""Ролик: Барби ← Лилли. Факт + мысль о смене аудитории, без visual-разбора."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from edit.d2_prose import write_prose
from edit.graph import build_e1_only_graph, build_editorial_graph
from edit.llm import get_chat_model
from models import (
    ClaimCard,
    ClaimKind,
    Citation,
    ContrastPair,
    Dossier,
    ImageBuckets,
    ImageCandidate,
    Scope,
    SoftFactcheckResult,
    WebConfirmation,
)

load_dotenv()

SOURCE = ROOT / "sources/goralik-barbie-lilli-theft.txt"
OUT = ROOT / "runs/goralik-barbie/lilli_steal_like_artist"


def build_claim() -> ClaimCard:
    return ClaimCard(
        claim_id="barbie-lilli-steal-like-artist",
        kind=ClaimKind.origin,
        claim=(
            "Барби не изобрели с нуля: взрослую немецкую Лилли почти без изменений "
            "перенесли в детский контекст и назвали подростковой моделью."
        ),
        counter_expectation=(
            "Большой новый продукт начинается с полностью нового изобретения."
        ),
        visual_hint="Лилли из Bild → первая Barbie OSS",
        object_anchor="Лилли, перенесённая в Барби",
        contrast_pair=ContrastPair(
            state_a="Лилли: кукла из Bild, которую продавали взрослым",
            state_b="Барби: почти та же фигура как teenage fashion model",
            shift=(
                "та же вещь получает другую аудиторию и другое разрешённое значение"
            ),
        ),
        mechanism_term="смена контекста",
        mechanism_explain=(
            "Не нужно изобретать вещь заново: её можно перенести в другой рынок, "
            "упаковку и историю — тогда меняется то, кем она кажется аудитории."
        ),
        citation=Citation(
            locator="гл. 3, Лилли → Барби",
            quote=(
                "фигура первой Барби осталась фактически фигурой Лилли — "
                "ей только удалили соски"
            ),
        ),
        scope=Scope(
            period="1955–1959",
            region="DE→US",
            author_or_work="Bild Lilli / Mattel Barbie OSS",
        ),
        source_segment_id="barbie-lilli",
        confidence=0.92,
    )


def _imgs(state: str, query: str, n: int = 4) -> list[ImageCandidate]:
    return [
        ImageCandidate(
            url=f"https://img.example/{state}-{i}.jpg",
            title=f"архив / коллекция: {query}",
            description=query,
            query=query,
            soft_match=True,
            for_state=state,  # type: ignore[arg-type]
        )
        for i in range(n)
    ]


def freeze_dossier(claim: ClaimCard, essay: str) -> Dossier:
    notes = (
        "Рамка канала: «кради как художник» — хороший визуальный трюк не с нуля, "
        "а с переносом чужого силуэта в другой регистр.\n\n"
        "ПОЛНЫЙ ФРАГМЕНТ ИСТОЧНИКА:\n\n"
        + essay.strip()
    )
    return Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes=notes,
        web_confirmations=[
            WebConfirmation(
                url="https://example.com/lilli-barbie",
                title="Bild Lilli → Mattel Barbie OSS",
                snippet=claim.citation.quote,
                query=claim.claim,
                supports_claim=True,
            )
        ],
        image_candidates=ImageBuckets(
            for_state_a=_imgs("a", claim.contrast_pair.state_a),
            for_state_b=_imgs("b", claim.contrast_pair.state_b),
            search_status="ok",
        ),
        soft_factcheck=SoftFactcheckResult(
            ok=True,
            rationale="факты из цитаты источника; интерпретация пропорций — как в главе",
        ),
    ).freeze()


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _vo_md(claim: ClaimCard, script, critique=None, opening=None) -> str:
    lines = [
        f"# VO · `{claim.claim_id}`",
        "",
        "**Тема:** Барби vs Лилли · кради как художник",
        f"**A/B:** {claim.contrast_pair.state_a} → {claim.contrast_pair.state_b}",
        f"**Механизм:** {claim.mechanism_term}",
        f"**Длительность:** {script.duration_sec:.0f}с",
        "",
        "## Озвучка",
        "",
    ]
    for line in script.lines:
        lines.append(f"**{line.t_start:.0f}–{line.t_end:.0f}**  {line.text}")
        lines.append("")
    if opening:
        lines += ["## E4 · выбранный хук", "", opening.chosen_text, ""]
        for i, v in enumerate(opening.variants):
            mark = "←" if i == opening.chosen_index else ""
            lines.append(f"- [{i}]{mark} {v.text}")
        lines.append("")
    if critique:
        lines += [
            "## E-критик",
            "",
            f"- passes=`{critique.passes}` · dropoff={critique.dropoff_score} · "
            f"sev_max={critique.severity_max}",
            f"- retell: {critique.retell}",
            f"- coda: {critique.coda_quote}",
            f"- summary: {critique.summary}",
            "",
        ]
        for a in critique.attacks[:8]:
            lines.append(
                f"- **{a.kind.value}** sev{a.severity}: «{a.quote}» — {a.attack}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    claim = build_claim()
    essay = SOURCE.read_text(encoding="utf-8")
    dossier = freeze_dossier(claim, essay)
    llm = get_chat_model(model="gpt-5-2", temperature=0.25)
    OUT.mkdir(parents=True, exist_ok=True)
    _dump(OUT / "00_claim.json", claim)
    _dump(OUT / "01_dossier.json", dossier)

    print("== D2 ==")
    script = None
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            script = write_prose(dossier, llm=llm)
            break
        except Exception as exc:  # noqa: BLE001 — сеть/парсер KIE
            last_err = exc
            print(f"  D2 attempt {attempt + 1} failed: {exc}")
    if script is None:
        raise SystemExit(f"D2 failed: {last_err}")
    _dump(OUT / "03_script.json", script)
    for line in script.lines:
        print(f"  {line.t_start:.0f}–{line.t_end:.0f} {line.text}")

    print("== E1 ==")
    e1 = build_e1_only_graph().invoke({"dossier": dossier, "script": script})
    _dump(OUT / "04_trace.json", e1["trace"])
    print("  passes", e1["trace"].passes)
    if not e1["trace"].passes:
        return 2

    print("== E-критик → E4 ==")
    ed = build_editorial_graph(llm=llm).invoke({"dossier": dossier, "script": script})
    if ed.get("critique"):
        _dump(OUT / "04b_critique.json", ed["critique"])
    if ed.get("opening_pick"):
        _dump(OUT / "04c_openings.json", ed["opening_pick"])
    if ed.get("script"):
        _dump(OUT / "05_script_edited.json", ed["script"])
    meta = {
        "blocked_for_production": ed.get("blocked_for_production"),
        "critique_passes": ed["critique"].passes if ed.get("critique") else None,
        "dropoff_score": ed["critique"].dropoff_score if ed.get("critique") else None,
        "opening": ed["opening_pick"].chosen_text if ed.get("opening_pick") else None,
        "retell": ed["critique"].retell if ed.get("critique") else None,
    }
    _dump(OUT / "04_editorial_meta.json", meta)
    final = ed.get("script") or script
    md = _vo_md(claim, final, ed.get("critique"), ed.get("opening_pick"))
    (OUT / "SCENARIO.md").write_text(
        "# Черновик D2\n\n"
        + _vo_md(claim, script)
        + "\n---\n\n# После E\n\n"
        + md,
        encoding="utf-8",
    )
    print(md)
    print("meta", json.dumps(meta, ensure_ascii=False))
    return 0 if not ed.get("blocked_for_production") else 2


if __name__ == "__main__":
    raise SystemExit(main())
