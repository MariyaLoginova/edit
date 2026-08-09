import pytest
from pydantic import ValidationError

from models import BeatRisk, DropReason, RetentionReport


def test_weak_script_fails():
    report = RetentionReport(
        script_id="s1",
        duration_sec=45.0,
        first3_has_hook=False,
        open_strength=1,
        risks=[
            BeatRisk(
                t_start=0.0,
                t_end=3.0,
                quote="Привет, в этом видео мы поговорим",
                reason=DropReason.slow_open,
                forward_question=None,
                severity=4,
                fix_hint="Открой объектом и разрывом ожидания, без раскачки",
            ),
            BeatRisk(
                t_start=20.0,
                t_end=28.0,
                quote="А ещё отдельно про цвет",
                reason=DropReason.second_thesis,
                forward_question=None,
                severity=4,
                fix_hint="Убери второй тезис или вынеси в отдельный ролик",
            ),
        ],
        dropoff_score=72,
        passes=False,
        summary="Медленное открытие и второй тезис в середине — зритель уйдёт.",
    )
    assert report.passes is False
    assert report.first3_has_hook is False
    assert any(r.reason is DropReason.second_thesis for r in report.risks)


def test_strong_script_passes():
    report = RetentionReport(
        script_id="s2",
        duration_sec=40.0,
        first3_has_hook=True,
        open_strength=5,
        risks=[],
        dropoff_score=8,
        passes=True,
        summary="Крючок в первом кадре, один тезис, кода-фраза на месте.",
    )
    assert report.passes is True
    assert report.risks == []


def test_severity_bounds():
    with pytest.raises(ValidationError):
        BeatRisk(
            t_start=0,
            t_end=1,
            quote="x",
            reason=DropReason.filler,
            severity=6,
            fix_hint="убрать",
        )
