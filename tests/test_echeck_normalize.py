from __future__ import annotations

from edit.e_check import check_monologue
from models import EndingType, MonologueDraft
from tests.claim_factory import make_claim, make_frozen_dossier
from tests.fakes import FakeLLM


def test_echeck_accepts_wrapped_issues_payload():
    claim = make_claim()
    dossier = make_frozen_dossier(
        claim,
        material_notes="Первичный текст с тремя деталями.",
    )
    text = (
        "Хук короткий и жёсткий. "
        + ("Факт из материала держит внимание зрителя. " * 40)
        + "Поэтому я бы вернула этот образ во взрослый регистр."
    )
    monologue = MonologueDraft(
        claim_id=claim.claim_id,
        text=text,
        word_count=len(text.split()),
        story_method="a_vot_nifiga",
        ending_type=EndingType.formula,
    )

    def router(messages):
        return """{
          "MonologueCheck": {
            "claim_id": "%s",
            "factcheck_summary": "Хронология перевёрнута.",
            "issues": [
              {
                "type": "factual_error",
                "severity": "high",
                "quote": "с 1972 по 1977",
                "problem": "Даты не совпадают с источником."
              }
            ]
          }
        }""" % claim.claim_id

    check = check_monologue(monologue, dossier, llm=FakeLLM(router))
    assert check.passes is False
    assert check.summary.startswith("Хронология")
    assert len(check.factual_issues) == 1
    assert check.factual_issues[0].severity == 4
