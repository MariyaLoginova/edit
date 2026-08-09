from __future__ import annotations

from edit.e2_retention_critic import compute_passes, critique_retention, finalize_report
from models import BeatRisk, DropReason, RetentionReport
from tests.fakes import FakeLLM


def _weak_report(script_id: str, duration_sec: float) -> dict:
    return {
        "script_id": script_id,
        "duration_sec": duration_sec,
        "first3_has_hook": False,
        "open_strength": 1,
        "risks": [
            {
                "t_start": 0.0,
                "t_end": 3.0,
                "quote": "Привет! В этом видео мы поговорим про историю моды.",
                "reason": "slow_open",
                "forward_question": None,
                "severity": 4,
                "fix_hint": "Открой разрывом ожидания, без приветствия",
            },
            {
                "t_start": 22.0,
                "t_end": 32.0,
                "quote": "А ещё отдельно про цвет: синий в геральдике значил совсем другое.",
                "reason": "second_thesis",
                "forward_question": None,
                "severity": 4,
                "fix_hint": "Убери второй тезис",
            },
            {
                "t_start": 32.0,
                "t_end": 45.0,
                "quote": "Ну вот, как-то так. Подписывайтесь, если интересно.",
                "reason": "flat_ending",
                "forward_question": None,
                "severity": 3,
                "fix_hint": "Сверни в одну цитируемую формулу",
            },
        ],
        "dropoff_score": 70,
        "passes": True,  # LLM ошибся — finalize обязан поправить
        "summary": "Медленное открытие и второй тезис — зритель уйдёт.",
    }


def _strong_report(script_id: str, duration_sec: float) -> dict:
    return {
        "script_id": script_id,
        "duration_sec": duration_sec,
        "first3_has_hook": True,
        "open_strength": 5,
        "risks": [],
        "dropoff_score": 10,
        "passes": False,  # LLM ошибся в другую сторону
        "summary": "Крючок в первом кадре, один тезис, кода-фраза.",
    }


def test_weak_script_fails_with_slow_open_and_second_thesis(script_weak):
    llm = FakeLLM(_weak_report(script_weak.script_id, script_weak.duration_sec))
    report = critique_retention(script_weak, llm=llm)
    assert report.first3_has_hook is False
    assert report.passes is False
    reasons = {r.reason for r in report.risks}
    assert DropReason.slow_open in reasons
    assert DropReason.second_thesis in reasons


def test_strong_script_passes(script_strong):
    llm = FakeLLM(_strong_report(script_strong.script_id, script_strong.duration_sec))
    report = critique_retention(script_strong, llm=llm)
    assert report.passes is True
    assert report.first3_has_hook is True
    assert all(r.severity <= 2 for r in report.risks)


def test_severity_ge_4_blocks_regardless_of_score(script_strong):
    report = RetentionReport(
        script_id=script_strong.script_id,
        duration_sec=script_strong.duration_sec,
        first3_has_hook=True,
        open_strength=4,
        risks=[
            BeatRisk(
                t_start=10,
                t_end=12,
                quote="Платье почти не требовало ухода",
                reason=DropReason.no_forward,
                forward_question=None,
                severity=4,
                fix_hint="Добавь виток интриги",
            )
        ],
        dropoff_score=5,
        passes=True,
        summary="Один жёсткий отвал.",
    )
    assert compute_passes(report, threshold=40) is False
    finalized = finalize_report(report, script_strong, threshold=40)
    assert finalized.passes is False


def test_verdict_stable_across_two_runs(script_weak):
    payload = _weak_report(script_weak.script_id, script_weak.duration_sec)
    a = critique_retention(script_weak, llm=FakeLLM(payload))
    b = critique_retention(script_weak, llm=FakeLLM(payload))
    assert a.passes == b.passes
    assert a.passes is False


def test_risk_quotes_are_substrings_of_script(script_weak):
    report = critique_retention(
        script_weak,
        llm=FakeLLM(_weak_report(script_weak.script_id, script_weak.duration_sec)),
    )
    full = " ".join(line.text for line in script_weak.lines)
    for risk in report.risks:
        assert risk.quote in full
