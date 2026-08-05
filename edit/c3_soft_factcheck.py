"""C3 · Мягкая проверка фактов (одна LLM-развилка) + заморозка досье."""

from __future__ import annotations

from pathlib import Path

from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import Dossier, SoftFactcheckResult

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "c3_soft_factcheck.txt"


def soft_factcheck(
    dossier: Dossier,
    *,
    llm: ChatModel | None = None,
    auto_freeze: bool = True,
) -> Dossier:
    """C3: не видит сценарий (инвариант 2). При ok — freeze SSOT."""
    dossier.ensure_mutable()
    model = llm or get_chat_model(temperature=0.0)

    payload = {
        "claim_id": dossier.claim_id,
        "claim": dossier.claim.claim,
        "kind": dossier.claim.kind.value,
        "citation": dossier.claim.citation.model_dump(),
        "scope": dossier.claim.scope.model_dump(),
        "counter_expectation": dossier.claim.counter_expectation,
        "material_notes": dossier.material_notes,
        "web_confirmations": [
            c.model_dump() for c in dossier.web_confirmations if c.supports_claim
        ],
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(payload)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    result = SoftFactcheckResult.model_validate(raw)
    updated = dossier.model_copy(update={"soft_factcheck": result})
    if auto_freeze and result.ok:
        return updated.freeze()
    return updated
