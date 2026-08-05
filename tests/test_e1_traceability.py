from __future__ import annotations

from edit.e1_traceability import audit_traceability
from models import (
    Dossier,
    ScriptDraft,
    ScriptLine,
    SoftFactcheckResult,
    TraceReason,
)
from tests.claim_factory import make_claim, make_frozen_dossier


def _dossier(*, frozen: bool = True) -> Dossier:
    if frozen:
        return make_frozen_dossier()
    claim = make_claim()
    return Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes="ok",
        soft_factcheck=SoftFactcheckResult(ok=True, invented_items=[], rationale="ok"),
    )


def test_e1_passes_when_all_facts_traced():
    script = ScriptDraft(
        script_id="s1",
        claim_id="lbd-maintenance-not-luxury",
        duration_sec=10,
        lines=[
            ScriptLine(t_start=0, t_end=5, text="Не роскошь, а отсутствие горничной.", claim_id="lbd-maintenance-not-luxury"),
            ScriptLine(t_start=5, t_end=10, text="Платье почти не требовало ухода.", claim_id="lbd-maintenance-not-luxury"),
        ],
    )
    report = audit_traceability(script, _dossier())
    assert report.passes is True
    assert report.issues == []


def test_e1_fails_missing_claim_id():
    script = ScriptDraft(
        script_id="s2",
        claim_id="lbd-maintenance-not-luxury",
        duration_sec=5,
        lines=[
            ScriptLine(
                t_start=0,
                t_end=5,
                text="Маленькое чёрное взлетело из-за дешёвого ухода.",
                claim_id=None,
            )
        ],
    )
    report = audit_traceability(script, _dossier())
    assert report.passes is False
    assert report.issues[0].reason is TraceReason.missing_claim_id


def test_e1_fails_unknown_claim_id():
    script = ScriptDraft(
        script_id="s3",
        claim_id="lbd-maintenance-not-luxury",
        duration_sec=5,
        lines=[
            ScriptLine(
                t_start=0,
                t_end=5,
                text="А ещё синий в геральдике значил другое.",
                claim_id="heraldic-blue-aside",
            )
        ],
    )
    report = audit_traceability(script, _dossier())
    assert report.passes is False
    assert any(i.reason is TraceReason.unknown_claim_id for i in report.issues)


def test_e1_fails_if_dossier_not_frozen():
    script = ScriptDraft(
        script_id="s4",
        claim_id="lbd-maintenance-not-luxury",
        duration_sec=5,
        lines=[
            ScriptLine(
                t_start=0,
                t_end=5,
                text="Факт из досье.",
                claim_id="lbd-maintenance-not-luxury",
            )
        ],
    )
    report = audit_traceability(script, _dossier(frozen=False))
    assert report.passes is False
    assert any(i.reason is TraceReason.dossier_not_frozen for i in report.issues)


def test_e1_allows_opinion_marker_without_claim_id():
    script = ScriptDraft(
        script_id="s5",
        claim_id="lbd-maintenance-not-luxury",
        duration_sec=12,
        lines=[
            ScriptLine(
                t_start=0,
                t_end=6,
                text="Платье почти не требовало ухода.",
                claim_id="lbd-maintenance-not-luxury",
            ),
            ScriptLine(
                t_start=6,
                t_end=12,
                text="А если посмотреть так, переиздание старого — приём внимания.",
                claim_id=None,
            ),
        ],
    )
    report = audit_traceability(script, _dossier())
    assert report.passes is True
