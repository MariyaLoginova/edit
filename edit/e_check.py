"""E-проверка личного монолога: факты и перебор (FIX-5)."""

from __future__ import annotations

from pathlib import Path

from edit.llm import ChatModel, invoke_json
from edit.model_routing import get_personal_story_model
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
    if monologue.word_count < 120:
        return MonologueCheck(
            claim_id=monologue.claim_id,
            factual_issues=[],
            overclaim_issues=[
                FactIssue(
                    quote=monologue.text[:280] or "пустой монолог",
                    issue=(
                        f"Монолог слишком короткий ({monologue.word_count} слов): "
                        "в нём нельзя удержать три доказательные детали."
                    ),
                    severity=4,
                )
            ],
            passes=False,
            summary="Кодовый quality-gate заблокировал слишком короткий D2 без нового LLM-вызова.",
        )
    model = llm or get_personal_story_model(temperature=0.0)
    user = {
        "monologue": monologue.model_dump(mode="json"),
        "source_material": dossier.material_notes,
        "source_citation": dossier.claim.citation.model_dump(mode="json"),
        "web_confirmations": [
            item.model_dump(mode="json") for item in dossier.web_confirmations if item.supports_claim
        ],
    }
    try:
        raw = invoke_json(
            model,
            [
                {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": str(user)},
            ],
            retries=0,
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
    except Exception as exc:
        # Никакого «давай ещё раз» на той же модели: технический брак
        # прозрачно блокирует переход к человеку.
        return MonologueCheck(
            claim_id=monologue.claim_id,
            factual_issues=[
                FactIssue(
                    quote=monologue.text[:280] or "пустой монолог",
                    issue=f"Технический сбой E-проверки: {type(exc).__name__}: {exc}",
                    severity=5,
                )
            ],
            overclaim_issues=[],
            passes=False,
            summary="E-проверка не получила валидный ответ; следующий этап заблокирован.",
        )
