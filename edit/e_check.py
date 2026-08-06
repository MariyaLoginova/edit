"""E-проверка личного монолога: факты и перебор (FIX-5)."""

from __future__ import annotations

from pathlib import Path

from edit.llm import ChatModel, get_chat_model, invoke_json
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
    user = {
        "monologue": monologue.model_dump(mode="json"),
        "source_material": dossier.material_notes,
        "source_citation": dossier.claim.citation.model_dump(mode="json"),
    }
    last_error: Exception | None = None
    for _ in range(3):
        request = user if last_error is None else {
            **user,
            "revision_note": f"Предыдущая проверка невалидна: {last_error}",
            "output_contract": {
                "required": ["factual_issues", "overclaim_issues", "summary"],
                "summary": "непустой диагноз в 1–3 предложениях даже если проблем нет",
            },
        }
        try:
            raw = invoke_json(
                model,
                [
                    {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
                    {"role": "user", "content": str(request)},
                ],
                retries=2,
            )
            if not isinstance(raw, dict):
                raise ValueError("ожидался JSON-объект")
            raw.setdefault("claim_id", monologue.claim_id)
            for key in ("factual_issues", "overclaim_issues"):
                normalized_issues = []
                for item in raw.get(key, []):
                    if isinstance(item, dict):
                        item = dict(item)
                        item.setdefault(
                            "issue",
                            item.get("reason")
                            or item.get("explanation")
                            or item.get("comment")
                            or "Проверка не объяснила проблему.",
                        )
                        severity = item.get("severity", 3)
                        if isinstance(severity, str):
                            severity = {
                                "low": 2,
                                "medium": 3,
                                "high": 4,
                                "critical": 5,
                            }.get(severity.lower(), 3)
                        item["severity"] = severity
                    normalized_issues.append(
                        FactIssue.model_validate(item).model_dump(mode="json")
                    )
                raw[key] = normalized_issues
            if not raw.get("summary"):
                raise ValueError("пустой summary")
            blocked = any(
                issue.severity >= 4
                for issue in [
                    *[FactIssue.model_validate(x) for x in raw["factual_issues"]],
                    *[FactIssue.model_validate(x) for x in raw["overclaim_issues"]],
                ]
            )
            raw["passes"] = not blocked
            return MonologueCheck.model_validate(raw)
        except (ValueError, Exception) as exc:
            last_error = exc
    assert last_error is not None
    raise last_error
