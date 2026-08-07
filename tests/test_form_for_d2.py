from __future__ import annotations

from tests.brief_factory import make_argument_brief, make_excursion_brief


def test_for_d2_excludes_service_fields():
    brief = make_excursion_brief()
    payload = brief.for_d2()
    assert set(payload) >= {
        "claim_id",
        "format",
        "main_thought",
        "angle",
        "opening",
        "exhibits",
        "conclusion",
    }
    assert "why_viewer" not in payload
    assert "audience_reason" not in payload
    assert "share_reason" not in payload
    assert "idea_pitch" not in payload
    assert "recommended_method" not in payload
    assert "proof_plan" not in payload
    assert len(payload["exhibits"]) == 6
    assert "plain" in payload["conclusion"]
    assert "do_not_voice_quote" in payload["conclusion"]


def test_for_d2_argument_has_proof_plan_not_exhibits():
    brief = make_argument_brief()
    payload = brief.for_d2()
    assert "proof_plan" in payload
    assert "exhibits" not in payload
    assert len(payload["proof_plan"]) == 3
