from __future__ import annotations

from pathlib import Path

from edit.e_check import PROMPT_PATH, check_monologue
from models import EndingType, MonologueDraft
from tests.claim_factory import make_claim, make_frozen_dossier
from tests.fakes import FakeLLM


def test_echeck_prompt_ignores_figurative_authorial_framing():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    assert "дочка проститутки" in prompt
    assert "НЕ ТРОГАТЬ" in prompt
    assert "даты" in prompt.lower()
    assert "вывод шире тезиса" in prompt


def test_echeck_user_payload_scopes_hard_facts_only():
    claim = make_claim()
    dossier = make_frozen_dossier(claim, material_notes="Лилли, 1955, Bild Zeitung.")
    monologue = MonologueDraft(
        claim_id=claim.claim_id,
        text=("Барби — дочка проститутки. " * 40) + "Спиздели или вдохновились?",
        word_count=120,
        story_method="a_vot_nifiga",
        ending_type=EndingType.reactive,
    )
    seen: dict = {}

    def router(messages):
        seen["user"] = messages[1]["content"]
        return """{
          "claim_id": "%s",
          "factual_issues": [],
          "overclaim_issues": [],
          "passes": true,
          "summary": "Жёстких фактических ошибок нет."
        }""" % claim.claim_id

    check = check_monologue(monologue, dossier, llm=FakeLLM(router))
    assert check.passes is True
    assert "figurative framing" in seen["user"]
    assert "dates" in seen["user"]
