#!/usr/bin/env python3
"""Целая глава → одна озвучка → E1–E6 (без нарезки на подтезисы).

A2 не дробит статью. Полный текст кладётся в досье как material_notes.
Один сквозной claim_id для трассируемости. Картинки — заглушка под A/B
(не курация). Цель прогона — редактура E.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from edit.d3_tov import apply_tov
from edit.graph import build_e1_only_graph, build_editorial_graph
from edit.llm import get_chat_model, invoke_json
from models import (
    ClaimCard,
    ClaimKind,
    Citation,
    ContrastPair,
    Dossier,
    ImageBuckets,
    ImageCandidate,
    Scope,
    ScriptDraft,
    SoftFactcheckResult,
    WebConfirmation,
)

load_dotenv()

SOURCE = ROOT / "sources/goralik-mimimi.txt"
OUT = ROOT / "runs/goralik-mimimi/article_editorial"

WHOLE_VO_PROMPT = """\
Ты пишешь ОЗВУЧКУ короткого ролика по ЦЕЛОМУ эссе (не по одному тезису).
Голос за кадром: коротко, живо, смотришь на картинку вместе со зрителем.

Дуга ролика = дуга эссе, одним дыханием (~90 сек):
1) хук — сток-щенок с поводочком «Гулять пойдем?» / минимальная социальная монета
2) педоморфизм — почему хочется защитить и «забрать домой»
3) хрупкость — мордочка из конфет на пирожном: целое → надкушенное
4) порог количества — один котик → пятьдесят; милота ломается
5) кода — одна уносимая фраза (благодарность / моление о мирном времени — по эссе)

Правила:
— Не дели на «отдельные ролики» и не объявляй список тезисов.
— Не канцелярит. Не «механизм:», не «формула:», не «как сказано в материале».
— Факты и имена — ТОЛЬКО из текста эссе (Райден, Бейсман и т.п. — только если
  реально нужны и есть в тексте; лучше через образы, чем через фамилии).
— Каждая строка lines должна иметь claim_id = "{claim_id}".
— Таймкоды сплошные с 0; duration_sec ≈ 85–100.
— Один сквозной сюжет, не набор слайдов.

Верни ТОЛЬКО JSON ScriptDraft:
{{
  "script_id": "script-goralik-mimimi-whole",
  "claim_id": "{claim_id}",
  "duration_sec": 90.0,
  "tov_applied": false,
  "lines": [
    {{"t_start":0.0,"t_end":4.0,"text":"...","claim_id":"{claim_id}","beat_id":"b1"}}
  ]
}}
"""


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    else:
        data = obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _images(state: str, query: str, n: int = 4) -> list[ImageCandidate]:
    return [
        ImageCandidate(
            url=f"https://img.example/{state}-{i}.jpg",
            title=f"сток / архив: {query}",
            description=query,
            query=query,
            soft_match=True,
            for_state=state,  # type: ignore[arg-type]
        )
        for i in range(n)
    ]


def build_throughline_claim() -> ClaimCard:
    """Один сквозной каркас на главу — не набор подтезисов."""
    return ClaimCard(
        claim_id="goralik-mimimi-whole",
        kind=ClaimKind.causal,
        claim=(
            "Котик на улице даёт микроумиление без вовлечения — "
            "пока тех же котиков не станет пятьдесят и милота не перевернётся в тревогу."
        ),
        counter_expectation=(
            "Чем больше милых картинок в ленте, тем теплее и безопаснее становится фон."
        ),
        visual_hint="один котик на улице → пятьдесят котиков",
        object_anchor="котик на улице",
        contrast_pair=ContrastPair(
            state_a="перед тобой один котик",
            state_b="перед тобой пятьдесят котиков",
            shift="микроумиление сменяется замиранием перед хищной массой",
        ),
        mechanism_term="порог-количества",
        mechanism_explain=(
            "При росте числа одинаковых фигур взгляд перестаёт держать одну мордочку "
            "и начинает читать плотность стаи."
        ),
        citation=Citation(
            locator="эссе целиком, финал",
            quote=(
                "Пятьдесят — ты останавливаешься и не знаешь, как идти дальше, "
                "потому что перед тобой пятьдесят, простите, хищных животных"
            ),
        ),
        scope=Scope(author_or_work="Линор Горалик"),
        source_segment_id="goralik-mimimi-whole",
        confidence=0.9,
    )


def freeze_dossier(claim: ClaimCard, essay: str) -> Dossier:
    notes = (
        "Полный текст эссе (глава целиком, без нарезки на подтезисы):\n\n" + essay.strip()
    )
    d = Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes=notes,
        web_confirmations=[
            WebConfirmation(
                url="https://linorgoralik.com/mimi.html",
                title="Линор Горалик · N мимими × M мимими",
                snippet=claim.citation.quote,
                query=claim.claim,
                supports_claim=True,
            )
        ],
        image_candidates=ImageBuckets(
            for_state_a=_images("a", claim.contrast_pair.state_a),
            for_state_b=_images("b", claim.contrast_pair.state_b),
            search_status="ok",
        ),
        soft_factcheck=SoftFactcheckResult(
            ok=True,
            rationale="материал = полный текст источника; выдуманных атрибуций нет",
        ),
    )
    return d.freeze()


def write_whole_vo(essay: str, claim: ClaimCard, *, llm) -> ScriptDraft:
    user = {
        "claim_id": claim.claim_id,
        "throughline": claim.claim,
        "object_anchor": claim.object_anchor,
        "contrast_pair": claim.contrast_pair.model_dump(mode="json"),
        "mechanism_term": claim.mechanism_term,
        "essay": essay.strip(),
    }
    raw = invoke_json(
        llm,
        [
            {
                "role": "system",
                "content": WHOLE_VO_PROMPT.format(claim_id=claim.claim_id),
            },
            {"role": "user", "content": str(user)},
        ],
        retries=2,
    )
    if isinstance(raw, dict):
        raw.setdefault("script_id", "script-goralik-mimimi-whole")
        raw.setdefault("claim_id", claim.claim_id)
        raw["tov_applied"] = False
        for line in raw.get("lines") or []:
            if isinstance(line, dict):
                line["claim_id"] = claim.claim_id
    script = ScriptDraft.model_validate(raw)
    return apply_tov(script, llm=llm)


def _report_md(claim, dossier, script0, e1, ed) -> str:
    script = ed.get("script") or script0
    trace = e1.get("trace")
    ret = ed.get("retention")
    red = ed.get("red_critique")
    op = ed.get("opening_pick")
    retell = ed.get("retell")
    comp = ed.get("compression")
    blocked = ed.get("blocked_for_production")

    lines = [
        "# Редактура E · глава целиком (`goralik-mimimi`)",
        "",
        f"**blocked_for_production:** `{blocked}`",
        f"**claim_id:** `{claim.claim_id}`",
        f"**длительность (после E):** {script.duration_sec:.0f}с",
        "",
        "Источник прогнан как одна глава: полный текст в `material_notes`, "
        "без нарезки A2 на подтезисы.",
        "",
        "## Сводка проходов",
        "",
        "| узел | passes | суть |",
        "|---|---|---|",
        f"| E1 трассируемость | `{getattr(trace, 'passes', None)}` | "
        f"issues={len(getattr(trace, 'issues', []) or [])} |",
        f"| E2 удержание | `{getattr(ret, 'passes', None)}` | "
        f"score={getattr(ret, 'dropoff_score', None)} |",
        f"| E3 красный | `{getattr(red, 'passes', None)}` | "
        f"severity_max={getattr(red, 'severity_max', None)} |",
        f"| E4 открытия | — | variants={len(getattr(op, 'variants', []) or [])}, "
        f"chosen={getattr(op, 'chosen_index', None)} |",
        f"| E5 пересказ | `{getattr(retell, 'passes', None)}` | "
        f"coda_quotable={getattr(retell, 'coda_is_quotable', None)} |",
        f"| E6 сжатие | `{getattr(comp, 'passes', None)}` | "
        f"reduction={getattr(comp, 'reduction_ratio', None)} |",
        "",
        "## E1 · Трассируемость",
        "",
    ]
    if trace:
        lines.append(f"- passes: `{trace.passes}`")
        lines.append(f"- summary: {getattr(trace, 'summary', '')}")
        for iss in trace.issues or []:
            lines.append(
                f"- issue[{iss.line_index}] {iss.reason}: {iss.detail or iss.text}"
            )
    lines += ["", "## E2 · Удержание (зачем смотреть дальше)", ""]
    if ret:
        lines.append(f"- dropoff_score: **{ret.dropoff_score}** · passes=`{ret.passes}`")
        lines.append(f"- summary: {ret.summary}")
        for m in (ret.risks or [])[:12]:
            reason = m.reason.value if hasattr(m.reason, "value") else m.reason
            fwd = m.forward_question or "—"
            lines.append(
                f"- `{m.t_start:.0f}–{m.t_end:.0f}` sev{m.severity} `{reason}`: "
                f"«{m.quote}» · держит: {fwd} · fix: {m.fix_hint}"
            )
    lines += ["", "## E3 · Красный критик", ""]
    if red:
        lines.append(f"- passes=`{red.passes}` · severity_max={red.severity_max}")
        lines.append(f"- summary: {red.summary}")
        for a in red.attacks:
            lines.append(
                f"- **{a.kind.value}** sev{a.severity}: «{a.quote}» — {a.attack}"
            )
    lines += ["", "## E4 · Перебор открытий", ""]
    if op:
        lines.append(f"- chosen_index: {op.chosen_index}")
        lines.append(f"- chosen: {op.chosen_text}")
        for i, v in enumerate(op.variants):
            mark = "←" if i == op.chosen_index else " "
            lines.append(f"- [{i}]{mark} (h{v.hook_strength}) {v.text} — {v.rationale}")
    lines += ["", "## E5 · Пересказ", ""]
    if retell:
        lines.append(f"- passes=`{retell.passes}`")
        lines.append(f"- retell: {retell.retell}")
        lines.append(f"- coda: {retell.coda_quote}")
        lines.append(f"- summary: {retell.summary}")
        if retell.fix_hint:
            lines.append(f"- fix_hint: {retell.fix_hint}")
    lines += ["", "## E6 · Сжатие", ""]
    if comp:
        lines.append(
            f"- passes=`{comp.passes}` · {comp.original_chars}→{comp.compressed_chars} "
            f"({comp.reduction_ratio:.0%})"
        )
        lines.append(f"- summary: {comp.summary}")
    lines += ["", "## Озвучка после редактуры", ""]
    for line in script.lines:
        lines.append(f"- `{line.t_start:.0f}–{line.t_end:.0f}` {line.text}")
    lines += ["", "## Озвучка до E4/E6 (черновик)", ""]
    for line in script0.lines:
        lines.append(f"- `{line.t_start:.0f}–{line.t_end:.0f}` {line.text}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    essay = SOURCE.read_text(encoding="utf-8")
    claim = build_throughline_claim()
    dossier = freeze_dossier(claim, essay)
    llm = get_chat_model(model="gpt-5-2", temperature=0.2)

    OUT.mkdir(parents=True, exist_ok=True)
    _dump(OUT / "00_claim.json", claim)
    _dump(OUT / "01_dossier.json", dossier)

    print("== VO по целой главе ==")
    script0 = write_whole_vo(essay, claim, llm=llm)
    _dump(OUT / "03_script_draft.json", script0)
    print(f"  lines={len(script0.lines)} duration={script0.duration_sec}s")
    for line in script0.lines:
        print(f"  {line.t_start:.0f}–{line.t_end:.0f} {line.text}")

    print("== E1 ==")
    e1 = build_e1_only_graph().invoke({"dossier": dossier, "script": script0})
    _dump(OUT / "04_trace.json", e1.get("trace"))
    print(f"  passes={e1['trace'].passes} issues={len(e1['trace'].issues)}")
    if not e1["trace"].passes:
        _dump(OUT / "04_editorial_meta.json", {"blocked": True, "at": "E1"})
        (OUT / "EDITORIAL.md").write_text(
            _report_md(claim, dossier, script0, e1, {}), encoding="utf-8"
        )
        print((OUT / "EDITORIAL.md").read_text(encoding="utf-8"))
        return 2

    print("== E2→E6 ==")
    ed = build_editorial_graph(llm=llm).invoke(
        {"dossier": dossier, "script": script0}
    )
    _dump(OUT / "04b_retention.json", ed.get("retention"))
    _dump(OUT / "04c_red.json", ed.get("red_critique"))
    _dump(OUT / "04d_openings.json", ed.get("opening_pick"))
    _dump(OUT / "04e_retell.json", ed.get("retell"))
    _dump(OUT / "04f_compression.json", ed.get("compression"))
    if ed.get("script"):
        _dump(OUT / "05_script_edited.json", ed["script"])
    meta = {
        "blocked_for_production": ed.get("blocked_for_production"),
        "trace_passes": True,
        "retention_passes": ed["retention"].passes if ed.get("retention") else None,
        "red_passes": ed["red_critique"].passes if ed.get("red_critique") else None,
        "retell_passes": ed["retell"].passes if ed.get("retell") else None,
        "compression_passes": ed["compression"].passes if ed.get("compression") else None,
        "dropoff_score": ed["retention"].dropoff_score if ed.get("retention") else None,
        "red_severity_max": ed["red_critique"].severity_max if ed.get("red_critique") else None,
        "reduction_ratio": ed["compression"].reduction_ratio if ed.get("compression") else None,
        "opening_chosen": ed["opening_pick"].chosen_text if ed.get("opening_pick") else None,
        "retell": ed["retell"].retell if ed.get("retell") else None,
    }
    _dump(OUT / "04_editorial_meta.json", meta)
    md = _report_md(claim, dossier, script0, e1, ed)
    (OUT / "EDITORIAL.md").write_text(md, encoding="utf-8")
    print(md)
    return 0 if not ed.get("blocked_for_production") else 2


if __name__ == "__main__":
    raise SystemExit(main())
