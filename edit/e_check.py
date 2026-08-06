"""E-проверка личного монолога: факты и перебор (FIX-5)."""

from __future__ import annotations

from pathlib import Path

from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import Dossier, FactIssue, MonologueCheck, MonologueDraft

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e_check.txt"


def check_monologue(
    monologue: MonologueDraft,
    dossier: Dossier,
    *,
    llm: ChatModel | None = None,
) -> MonologueCheck:
    if not dossier.frozen:
        raise ValueError("E-проверка: нужен frozen dossier")
    model = llm or get_chat_model(temperature=0.0)
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {
                "role": "user",
                "content": str(
                    {
                        "monologue": monologue.model_dump(mode="json"),
                        "source_material": dossier.material_notes,
                        "source_citation": dossier.claim.citation.model_dump(mode="json"),
                    }
                ),
            },
        ]
    )
    raw = parse_json_payload(content_text(response))
    if not isinstance(raw, dict):
        raise ValueError("E-проверка: ожидался JSON-объект")
    raw.setdefault("claim_id", monologue.claim_id)
    for key in ("factual_issues", "overclaim_issues"):
        raw[key] = [
            FactIssue.model_validate(item).model_dump(mode="json")
            for item in raw.get(key, [])
        ]
    raw.setdefault("passes", False)
    raw.setdefault("summary", "")
    report = MonologueCheck.model_validate(raw)
    blocked = any(
        issue.severity >= 4
        for issue in [*report.factual_issues, *report.overclaim_issues]
    )
    return report.model_copy(update={"passes": report.passes and not blocked})
