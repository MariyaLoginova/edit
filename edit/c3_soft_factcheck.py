"""C3 · Мягкая проверка фактов + гейт freeze (FIX-2)."""

from __future__ import annotations

from pathlib import Path

from edit.config import load_thresholds
from edit.llm import ChatModel, content_text, get_chat_model, parse_json_payload
from models import Dossier, SoftFactcheckResult, can_freeze

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "c3_soft_factcheck.txt"


def _min_images() -> int:
    return int(load_thresholds().get("material", {}).get("min_images_per_state", 3))


def soft_factcheck(
    dossier: Dossier,
    *,
    llm: ChatModel | None = None,
    auto_freeze: bool = True,
) -> Dossier:
    """C3: не видит сценарий. Freeze только если soft_ok И can_freeze."""
    dossier.ensure_mutable()
    model = llm or get_chat_model(temperature=0.0)

    payload = {
        "claim_id": dossier.claim_id,
        "claim": dossier.claim.claim,
        "kind": dossier.claim.kind.value,
        "object_anchor": dossier.claim.object_anchor,
        "mechanism_term": dossier.claim.mechanism_term,
        "source_citation": dossier.claim.citation.model_dump(),
        "scope": dossier.claim.scope.model_dump(),
        "counter_expectation": dossier.claim.counter_expectation,
        "material_notes": dossier.material_notes,
        "search_findings": [
            c.model_dump() for c in dossier.web_confirmations
        ],
        "check_both": "source_citation + search_findings — оставь только реальное",
    }
    response = model.invoke(
        [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
            {"role": "user", "content": str(payload)},
        ]
    )
    raw = parse_json_payload(content_text(response))
    result = SoftFactcheckResult.model_validate(raw)
    ready, problems = can_freeze(dossier, min_images_per_state=_min_images())
    updated = dossier.model_copy(
        update={
            "soft_factcheck": result,
            "freeze_blockers": [] if (result.ok and ready) else (
                ([] if result.ok else [f"soft_factcheck: {result.rationale}"]) + problems
            ),
        }
    )
    if auto_freeze and result.ok and ready:
        return updated.freeze()
    return updated
