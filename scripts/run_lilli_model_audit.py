#!/usr/bin/env python3
"""Полный аудит личного контура Барби←Лилли по нескольким KIE-моделям."""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from edit.c1_material import collect_material
from edit.d2_monologue import write_monologue
from edit.e_check import check_monologue
from edit.e_editor import plan_story
from edit.llm import content_text, get_chat_model
from edit.search import SearchHit
from models import ClaimCard, SoftFactcheckResult

load_dotenv(ROOT / ".env")

MODELS = ("grok-4-5", "gemini-3-6-flash", "gpt-5-2")
CLAIM_PATH = ROOT / "runs/goralik-barbie/lilli_steal_like_artist/00_claim.json"
SOURCE_PATH = ROOT / "sources/goralik-barbie-lilli-theft.txt"
OUT = ROOT / "runs/goralik-barbie/lilli-model-audit"


@dataclass
class AuditedLLM:
    """Прозрачная обёртка: сохраняет каждый message и сырой ответ."""

    model: Any
    model_id: str
    stage: str = ""
    calls: list[dict[str, Any]] = field(default_factory=list)

    def invoke(self, messages: list[dict[str, str]]) -> Any:
        item: dict[str, Any] = {
            "model": self.model_id,
            "stage": self.stage,
            "messages": messages,
        }
        try:
            response = self.model.invoke(messages)
            item["received"] = content_text(response)
            self.calls.append(item)
            return response
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
            self.calls.append(item)
            raise


class SourceSearcher:
    def __init__(self, source: str):
        self.source = source

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        return [
            SearchHit(
                url="local://goralik-polaya-zhenshchina/ch03",
                title="Горалик · Полая женщина · глава 3",
                snippet=self.source,
            )
        ]


def dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def row(
    *,
    model: str,
    stage: str,
    sent_system: str,
    sent_user: str,
    received: str,
    next_stage: str,
    status: str,
) -> dict[str, str]:
    return {
        "model": model,
        "stage": stage,
        "sent_system": sent_system,
        "sent_user": sent_user,
        "received": received,
        "next_stage": next_stage,
        "status": status,
    }


def main() -> int:
    claim = ClaimCard.model_validate_json(CLAIM_PATH.read_text(encoding="utf-8"))
    source = SOURCE_PATH.read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT / "00_claim.json", claim)
    (OUT / "00_source_block.txt").write_text(source, encoding="utf-8")

    audit_rows: list[dict[str, str]] = []
    for model_id in MODELS:
        model_dir = OUT / model_id
        audited = AuditedLLM(get_chat_model(model=model_id, temperature=0.0), model_id)
        try:
            # C1 намеренно без LLM: полный исходник передаётся дальше, без выжимки.
            draft = collect_material(
                claim, searcher=SourceSearcher(source), llm=None
            )
            dossier = draft.model_copy(
                update={
                    "material_notes": source,
                    "soft_factcheck": SoftFactcheckResult(
                        ok=True,
                        rationale="Первичный текст передан E-проверке без LLM-выжимки.",
                    ),
                }
            ).freeze(require_images=False)
            dump(model_dir / "01_dossier.json", dossier)
            audit_rows.append(
                row(
                    model=model_id,
                    stage="C1 (code, no LLM)",
                    sent_system="—",
                    sent_user=source,
                    received=json.dumps(dossier.model_dump(mode="json"), ensure_ascii=False),
                    next_stage="E-editor",
                    status="ok",
                )
            )

            audited.stage = "E-editor"
            brief = plan_story(claim, llm=audited)
            dump(model_dir / "02_story_brief.json", brief)

            audited.stage = "D2 monologue"
            monologue = write_monologue(dossier, brief, llm=audited)
            dump(model_dir / "03_monologue.json", monologue)

            audited.stage = "E-check"
            check = check_monologue(monologue, dossier, llm=audited)
            dump(model_dir / "04_e_check.json", check)
            dump(
                model_dir / "05_result.json",
                {
                    "model": model_id,
                    "passes": check.passes,
                    "words": monologue.word_count,
                    "method": monologue.story_method,
                },
            )
            next_stage = "human review" if check.passes else "rewrite D2"
            status = "ok" if check.passes else "blocked"
        except Exception as exc:
            next_stage = "stop"
            status = f"error: {type(exc).__name__}"
            audit_rows.append(
                row(
                    model=model_id,
                    stage=audited.stage or "model preflight",
                    sent_system="—",
                    sent_user="—",
                    received=str(exc),
                    next_stage=next_stage,
                    status=status,
                )
            )

        for call in audited.calls:
            messages = call["messages"]
            system = "\n\n".join(
                m["content"] for m in messages if m.get("role") == "system"
            )
            user = "\n\n".join(
                m["content"] for m in messages if m.get("role") == "user"
            )
            audit_rows.append(
                row(
                    model=model_id,
                    stage=call["stage"],
                    sent_system=system,
                    sent_user=user,
                    received=call.get("received", call.get("error", "")),
                    next_stage=(
                        "D2 monologue"
                        if call["stage"] == "E-editor"
                        else "E-check"
                        if call["stage"] == "D2 monologue"
                        else next_stage
                    ),
                    status="ok" if "received" in call else "error",
                )
            )
        dump(model_dir / "calls.json", audited.calls)

    fields = ["model", "stage", "sent_system", "sent_user", "received", "next_stage", "status"]
    with (OUT / "audit.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit_rows)
    print(OUT / "audit.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
