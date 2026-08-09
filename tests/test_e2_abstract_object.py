from models import DropReason, RetentionReport, ScriptDraft, ScriptLine
from edit.e2_retention_critic import abstract_object_risks, finalize_report


def test_abstract_object_risks_flag_ungrounded_lines():
    script = ScriptDraft(
        script_id="s",
        claim_id="c",
        duration_sec=10,
        lines=[
            ScriptLine(t_start=0, t_end=5, text="Один кот смотрит на улице", claim_id="c"),
            ScriptLine(t_start=5, t_end=10, text="Эмоция становится глубже и сложнее", claim_id="c"),
        ],
    )
    risks = abstract_object_risks(script, object_anchors={"кот", "улице", "пятьдесят"})
    assert len(risks) == 1
    assert risks[0].reason is DropReason.abstract
    assert risks[0].severity >= 4


def test_finalize_injects_abstract_and_fails_passes():
    script = ScriptDraft(
        script_id="s",
        claim_id="c",
        duration_sec=6,
        lines=[
            ScriptLine(t_start=0, t_end=6, text="Всё становится многомерным чувством", claim_id="c"),
        ],
    )
    base = RetentionReport(
        script_id="s",
        duration_sec=6,
        first3_has_hook=True,
        open_strength=3,
        risks=[],
        dropoff_score=10,
        passes=True,
        summary="ok",
    )
    out = finalize_report(
        base, script, threshold=40, object_anchors={"кот", "пирожное"}
    )
    assert out.passes is False
    assert any(r.reason is DropReason.abstract for r in out.risks)
