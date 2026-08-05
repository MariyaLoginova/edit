#!/usr/bin/env python3
"""Глава целиком → одна озвучка → E1–E6 (без нарезки на подтезисы).

Полный текст главы в material_notes. Один сквозной claim_id.
Картинки — заглушка под A/B (не курация). Цель — редактура E.
"""

from __future__ import annotations

import argparse
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

PROFILES = {
    "mimimi": {
        "source": ROOT / "sources/goralik-mimimi.txt",
        "out": ROOT / "runs/goralik-mimimi/article_editorial",
        "claim": {
            "claim_id": "goralik-mimimi-whole",
            "claim": (
                "Котик на улице даёт микроумиление без вовлечения — "
                "пока тех же котиков не станет пятьдесят и милота не перевернётся в тревогу."
            ),
            "counter_expectation": (
                "Чем больше милых картинок в ленте, тем теплее и безопаснее становится фон."
            ),
            "visual_hint": "один котик на улице → пятьдесят котиков",
            "object_anchor": "котик на улице",
            "contrast_pair": {
                "state_a": "перед тобой один котик",
                "state_b": "перед тобой пятьдесят котиков",
                "shift": "микроумиление сменяется замиранием перед хищной массой",
            },
            "mechanism_term": "порог-количества",
            "mechanism_explain": (
                "При росте числа одинаковых фигур взгляд перестаёт держать одну мордочку "
                "и начинает читать плотность стаи."
            ),
            "quote": (
                "Пятьдесят — ты останавливаешься и не знаешь, как идти дальше, "
                "потому что перед тобой пятьдесят, простите, хищных животных"
            ),
            "locator": "эссе целиком, финал",
            "author": "Линор Горалик",
        },
        "arc": (
            "1) хук — сток-щенок / минимальная социальная монета\n"
            "2) педоморфизм — защитить и «забрать домой»\n"
            "3) хрупкость — мордочка из конфет: целое → надкушенное\n"
            "4) порог количества — один котик → пятьдесят\n"
            "5) кода — одна уносимая фраза"
        ),
    },
    "barbie-ch03": {
        "source": ROOT / "sources/goralik-barbie-ch03-appearance.txt",
        "out": ROOT / "runs/goralik-barbie/ch03_editorial",
        "claim": {
            "claim_id": "barbie-face-must-stay-recognizable",
            "claim": (
                "Лицо Барби меняли много раз — от OSS с косым взглядом до улыбки Малибу — "
                "но кукла обязана оставаться узнаваемой: лучше, но не другой."
            ),
            "counter_expectation": (
                "Считают, что лицо Барби в каждый год просто копировало идеал красоты эпохи."
            ),
            "visual_hint": "OSS Барби в полосатом купальнике vs Малибу Барби, смотрящая прямо",
            "object_anchor": "лицо Барби OSS в полосатом купальнике",
            "contrast_pair": {
                "state_a": "первая Барби OSS смотрит в сторону и вниз, тяжёлый макияж",
                "state_b": "Малибу Барби 1972 смотрит в глаза и улыбается",
                "shift": "пугающая взрослость сменяется пляжной «естественностью», но силуэт тот же бренд",
            },
            "mechanism_term": "узнаваемость-вместо-моды",
            "mechanism_explain": (
                "После каждого скачка лицо улучшают точечно: взгляд, улыбка, макияж — "
                "чтобы девочка в музее не сказала «это не Барби»."
            ),
            "quote": (
                "Барби должна была становиться лучше, но она не имела права стать другой"
            ),
            "locator": "гл. 3, изменения внешности",
            "author": "Линор Горалик · Полая женщина",
        },
        "arc": (
            "1) хук — девочка в музее: «Это не Барби» про первую OSS\n"
            "2) ложное — «лицо всегда = идеал красоты своего года»\n"
            "3) A/B — OSS (косит, тяжёлый макияж) → Малибу 1972 (смотрит прямо, улыбка)\n"
            "   опционально короткий хвост: откуда странные пропорции (Лилли/комикс 50-х)\n"
            "4) механизм — узнаваемость: лучше, но не другой\n"
            "5) кода — одна уносимая фраза про усреднённый тип / бренд-лицо"
        ),
    },
}


WHOLE_VO_PROMPT = """\
Ты пишешь ОЗВУЧКУ короткого ролика по ЦЕЛОЙ главе (не по одному тезису).
Голос за кадром: коротко, живо, смотришь на картинку вместе со зрителем.

Дуга ролика = дуга главы, одним дыханием (~80–100 сек):
{arc}

Правила:
— Не дели на «отдельные ролики» и не объявляй список тезисов.
— Не канцелярит. Не «механизм:», не «формула:», не «как сказано в материале».
— Факты, даты, имена — ТОЛЬКО из текста главы.
— Каждая строка lines должна иметь claim_id = "{claim_id}".
— Таймкоды сплошные с 0; duration_sec ≈ 80–100.
— Один сквозной сюжет, не набор слайдов.
— Сначала объект на экране, потом смысл.

Верни ТОЛЬКО JSON ScriptDraft:
{{
  "script_id": "script-{claim_id}",
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


def build_claim(cfg: dict) -> ClaimCard:
    c = cfg["claim"]
    return ClaimCard(
        claim_id=c["claim_id"],
        kind=ClaimKind.causal,
        claim=c["claim"],
        counter_expectation=c["counter_expectation"],
        visual_hint=c["visual_hint"],
        object_anchor=c["object_anchor"],
        contrast_pair=ContrastPair(**c["contrast_pair"]),
        mechanism_term=c["mechanism_term"],
        mechanism_explain=c["mechanism_explain"],
        citation=Citation(locator=c["locator"], quote=c["quote"]),
        scope=Scope(author_or_work=c["author"]),
        source_segment_id=c["claim_id"],
        confidence=0.9,
    )


def freeze_dossier(claim: ClaimCard, chapter: str) -> Dossier:
    notes = "Полный текст главы (целиком, без нарезки на подтезисы):\n\n" + chapter.strip()
    d = Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes=notes,
        web_confirmations=[
            WebConfirmation(
                url="https://example.com/source",
                title=claim.scope.author_or_work or "source",
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
            rationale="материал = полный текст главы; выдуманных атрибуций нет",
        ),
    )
    return d.freeze()


def write_whole_vo(chapter: str, claim: ClaimCard, *, arc: str, llm) -> ScriptDraft:
    user = {
        "claim_id": claim.claim_id,
        "throughline": claim.claim,
        "object_anchor": claim.object_anchor,
        "contrast_pair": claim.contrast_pair.model_dump(mode="json"),
        "mechanism_term": claim.mechanism_term,
        "chapter": chapter.strip(),
    }
    raw = invoke_json(
        llm,
        [
            {
                "role": "system",
                "content": WHOLE_VO_PROMPT.format(claim_id=claim.claim_id, arc=arc),
            },
            {"role": "user", "content": str(user)},
        ],
        retries=2,
    )
    if isinstance(raw, dict):
        raw.setdefault("script_id", f"script-{claim.claim_id}")
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
        f"# Редактура E · `{claim.claim_id}`",
        "",
        f"**blocked_for_production:** `{blocked}`",
        f"**длительность (после E):** {script.duration_sec:.0f}с",
        "",
        "Глава прогнана целиком: полный текст в `material_notes`, без нарезки A2.",
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
    lines += ["", "## E2 · Удержание", ""]
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
        lines.append(f"- chosen: {op.chosen_text}")
        for i, v in enumerate(op.variants):
            mark = "←" if i == op.chosen_index else " "
            lines.append(f"- [{i}]{mark} (h{v.hook_strength}) {v.text}")
    lines += ["", "## E5 · Пересказ", ""]
    if retell:
        lines.append(f"- passes=`{retell.passes}`")
        lines.append(f"- retell: {retell.retell}")
        lines.append(f"- coda: {retell.coda_quote}")
        lines.append(f"- summary: {retell.summary}")
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
    lines += ["", "## Озвучка до E4/E6", ""]
    for line in script0.lines:
        lines.append(f"- `{line.t_start:.0f}–{line.t_end:.0f}` {line.text}")
    lines.append("")
    return "\n".join(lines)


def run_profile(name: str, *, model: str) -> int:
    cfg = PROFILES[name]
    chapter = cfg["source"].read_text(encoding="utf-8")
    claim = build_claim(cfg)
    dossier = freeze_dossier(claim, chapter)
    llm = get_chat_model(model=model, temperature=0.2)
    out: Path = cfg["out"]
    out.mkdir(parents=True, exist_ok=True)
    _dump(out / "00_claim.json", claim)
    _dump(out / "01_dossier.json", dossier)

    print(f"== [{name}] VO по целой главе ==")
    script0 = write_whole_vo(chapter, claim, arc=cfg["arc"], llm=llm)
    _dump(out / "03_script_draft.json", script0)
    print(f"  lines={len(script0.lines)} duration={script0.duration_sec}s")
    for line in script0.lines:
        print(f"  {line.t_start:.0f}–{line.t_end:.0f} {line.text}")

    print(f"== [{name}] E1 ==")
    e1 = build_e1_only_graph().invoke({"dossier": dossier, "script": script0})
    _dump(out / "04_trace.json", e1.get("trace"))
    print(f"  passes={e1['trace'].passes} issues={len(e1['trace'].issues)}")
    if not e1["trace"].passes:
        (out / "EDITORIAL.md").write_text(
            _report_md(claim, dossier, script0, e1, {"blocked_for_production": True}),
            encoding="utf-8",
        )
        return 2

    print(f"== [{name}] E2→E6 ==")
    ed = build_editorial_graph(llm=llm).invoke({"dossier": dossier, "script": script0})
    _dump(out / "04b_retention.json", ed.get("retention"))
    _dump(out / "04c_red.json", ed.get("red_critique"))
    _dump(out / "04d_openings.json", ed.get("opening_pick"))
    _dump(out / "04e_retell.json", ed.get("retell"))
    _dump(out / "04f_compression.json", ed.get("compression"))
    if ed.get("script"):
        _dump(out / "05_script_edited.json", ed["script"])
    meta = {
        "profile": name,
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
    _dump(out / "04_editorial_meta.json", meta)
    md = _report_md(claim, dossier, script0, e1, ed)
    (out / "EDITORIAL.md").write_text(md, encoding="utf-8")
    print(md)
    return 0 if not ed.get("blocked_for_production") else 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--profile",
        default="barbie-ch03",
        choices=sorted(PROFILES),
        help="Какую главу прогнать",
    )
    p.add_argument("--model", default="gpt-5-2")
    args = p.parse_args()
    return run_profile(args.profile, model=args.model)


if __name__ == "__main__":
    raise SystemExit(main())
