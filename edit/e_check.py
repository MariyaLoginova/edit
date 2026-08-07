"""E-проверка личного монолога: только жёсткие факты (даты/имена/места)."""

from __future__ import annotations

import re
from pathlib import Path

from edit.llm import ChatModel, invoke_json
from edit.model_routing import get_personal_story_model
from models import Dossier, FactIssue, MonologueCheck, MonologueDraft

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "e_check.txt"

# Источник/автор книги — в описание ролика, не в озвучку.
_SOURCE_IN_SPEECH = re.compile(
    r"(?i)("
    r"читаю\s+у|по\s+данным|в\s+исследовани\w*|в\s+книге|источник\s+говор"
    r"|как\s+пишет|по\s+горалик|у\s+горалик|горалик\s+пиш"
    r"|лин[оа]р\s+горалик|полая\s+женщина"
    r")"
)
def _code_gates(monologue: MonologueDraft) -> list[FactIssue]:
    issues: list[FactIssue] = []
    text = monologue.text or ""
    if monologue.word_count < 200:
        issues.append(
            FactIssue(
                quote=text[:280] or "пустой монолог",
                issue=(
                    f"Монолог слишком короткий ({monologue.word_count} слов): "
                    "нужно 200–300 слов мяса, не конспект."
                ),
                severity=4,
            )
        )
    source_hit = _SOURCE_IN_SPEECH.search(text)
    if source_hit:
        start = max(0, source_hit.start() - 40)
        end = min(len(text), source_hit.end() + 80)
        issues.append(
            FactIssue(
                quote=text[start:end].strip(),
                issue=(
                    "В озвучке назван источник/автор книги. "
                    "Источники — в описание ролика, не в речь."
                ),
                severity=4,
            )
        )
    return issues


def check_monologue(
    monologue: MonologueDraft,
    dossier: Dossier,
    *,
    llm: ChatModel | None = None,
) -> MonologueCheck:
    if not dossier.frozen:
        raise ValueError("E-проверка: нужен frozen dossier")
    gate_issues = _code_gates(monologue)
    if gate_issues:
        return MonologueCheck(
            claim_id=monologue.claim_id,
            factual_issues=[],
            overclaim_issues=gate_issues,
            passes=False,
            summary="Кодовый quality-gate заблокировал монолог без нового LLM-вызова.",
        )
    model = llm or get_personal_story_model(temperature=0.0)
    user = {
        "monologue": monologue.model_dump(mode="json"),
        "source_material": dossier.material_notes,
        "source_citation": dossier.claim.citation.model_dump(mode="json"),
        "web_confirmations": [
            item.model_dump(mode="json") for item in dossier.web_confirmations if item.supports_claim
        ],
        "check_scope": {
            "only": ["dates", "names", "places", "colors", "numbers", "hard attributions"],
            "ignore": [
                "figurative framing",
                "authorial opinion",
                "sarcasm",
                "rhetorical questions",
                "style / slogans / density",
            ],
        },
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
        for wrapper in ("MonologueCheck", "monologue_check", "check", "result"):
            if isinstance(raw.get(wrapper), dict):
                raw = raw[wrapper]
                break
        raw.setdefault("claim_id", monologue.claim_id)
        if not raw.get("summary"):
            raw["summary"] = (
                raw.get("factcheck_summary")
                or raw.get("overall_assessment")
                or raw.get("overall_summary")
                or raw.get("verdict")
                or raw.get("comment")
                or ""
            )
        if isinstance(raw.get("summary"), str):
            raw["summary"] = raw["summary"][:500]
        if "factual_issues" not in raw and "overclaim_issues" not in raw:
            factual: list[dict] = []
            overclaim: list[dict] = []
            for item in raw.get("issues") or raw.get("problems") or []:
                if not isinstance(item, dict):
                    continue
                kind = str(
                    item.get("type") or item.get("kind") or item.get("category") or ""
                ).lower()
                bucket = overclaim if "overclaim" in kind or "density" in kind else factual
                bucket.append(item)
            raw["factual_issues"] = factual
            raw["overclaim_issues"] = overclaim
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
                        or item.get("problem")
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
            passed = raw.get("passed_checks") or []
            if isinstance(passed, list) and passed:
                raw["summary"] = "Проверка завершена; см. issues и passed_checks."
            else:
                raw["summary"] = "Проверка завершена без текстового summary."
        if isinstance(raw.get("summary"), str):
            raw["summary"] = raw["summary"][:500]
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
