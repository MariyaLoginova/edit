from __future__ import annotations

import pytest
from pydantic import ValidationError

from edit.e3_red_critic import critique_content, finalize_red
from edit.e4_openings import _apply_opening, rewrite_openings
from edit.e5_retell import evaluate_retell, finalize_retell
from edit.e6_compress import compress_script, finalize_compression
from models import (
    Citation,
    ClaimCard,
    ClaimKind,
    CompressionReport,
    Dossier,
    OpeningPick,
    OpeningVariant,
    RedAttack,
    RedAttackKind,
    RedCritique,
    RetentionReport,
    RetellReport,
    Scope,
    ScriptDraft,
    ScriptLine,
    SoftFactcheckResult,
)
from tests.fakes import FakeLLM


def _dossier() -> Dossier:
    claim = ClaimCard(
        claim_id="lbd-maintenance-not-luxury",
        kind=ClaimKind.causal,
        claim="Маленькое чёрное взлетело как наряд без ухода",
        counter_expectation="Думают про роскошь",
        visual_hint="Chanel LBD Vogue 1926",
        citation=Citation(locator="гл.2", quote="required almost no maintenance"),
        scope=Scope(period="1920s", author_or_work="Chanel"),
        source_segment_id="ch2-s1",
        confidence=0.9,
    )
    return Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes="low maintenance",
        soft_factcheck=SoftFactcheckResult(ok=True, rationale="ok"),
    ).freeze()


def _script() -> ScriptDraft:
    return ScriptDraft(
        script_id="s1",
        claim_id="lbd-maintenance-not-luxury",
        duration_sec=40,
        lines=[
            ScriptLine(t_start=0, t_end=3, text="Привет, сегодня про платье.", claim_id="lbd-maintenance-not-luxury"),
            ScriptLine(t_start=3, t_end=12, text="Казалось бы, это про роскошь.", claim_id="lbd-maintenance-not-luxury"),
            ScriptLine(t_start=12, t_end=24, text="На деле — почти не требовало ухода.", claim_id="lbd-maintenance-not-luxury"),
            ScriptLine(t_start=24, t_end=32, text="Чёрный прятал городскую грязь.", claim_id="lbd-maintenance-not-luxury"),
            ScriptLine(t_start=32, t_end=40, text="Формула: статус маскирует сервис, который исчез.", claim_id="lbd-maintenance-not-luxury"),
        ],
    )


def test_e3_finalize_blocks_on_severity_4():
    report = RedCritique(
        script_id="s1",
        attacks=[
            RedAttack(
                kind=RedAttackKind.banal,
                quote="Привет, сегодня про платье.",
                attack="Пустое открытие без тезиса.",
                severity=4,
            )
        ],
        severity_max=1,
        passes=True,
        summary="слабо",
    )
    out = finalize_red(report)
    assert out.passes is False
    assert out.severity_max == 4


def test_e3_critique_content(monkeypatch):
    payload = {
        "script_id": "s1",
        "attacks": [],
        "severity_max": 1,
        "passes": True,
        "summary": "Тезис держится на пруфе ухода.",
    }
    report = critique_content(_script(), _dossier(), llm=FakeLLM(payload))
    assert report.passes is True


def test_e4_requires_five_to_eight_variants():
    with pytest.raises(ValidationError):
        OpeningPick(
            script_id="s1",
            variants=[
                OpeningVariant(text="a", rationale="r", hook_strength=3)
            ],
            chosen_index=0,
            script=_script(),
        )


def test_e4_apply_opening_replaces_first_seconds():
    script = _script()
    out = _apply_opening(script, "Не роскошь — отсутствие горничной.")
    assert out.lines[0].t_start == 0.0
    assert out.lines[0].text.startswith("Не роскошь")
    assert out.lines[0].t_end <= 3.0 + 1e-6


def test_e4_rewrite_openings_picks_variant():
    variants = [
        {"text": f"Крючок вариант {i}", "rationale": "разрыв", "hook_strength": 4}
        for i in range(5)
    ]
    payload = {
        "script_id": "s1",
        "variants": variants,
        "chosen_index": 2,
        "script": _script().model_dump(mode="json"),
    }
    pick = rewrite_openings(
        _script(),
        _dossier(),
        RetentionReport(
            script_id="s1",
            duration_sec=40,
            first3_has_hook=False,
            open_strength=1,
            risks=[],
            dropoff_score=50,
            passes=False,
            summary="slow open",
        ),
        llm=FakeLLM(payload),
    )
    assert len(pick.variants) == 5
    assert pick.chosen_index == 2
    assert "вариант 2" in pick.script.lines[0].text


def test_e5_retell_finalize():
    report = RetellReport(
        script_id="s1",
        retell="LBD взлетело из-за ухода, не роскоши.",
        coda_quote="Формула: статус маскирует сервис, который исчез.",
        coda_is_quotable=True,
        retell_matches_coda=True,
        passes=False,
        summary="ok",
    )
    assert finalize_retell(report).passes is True


def test_e5_evaluate_retell():
    payload = {
        "script_id": "s1",
        "retell": "Статус маскирует исчезнувший сервис ухода.",
        "coda_quote": "Формула: статус маскирует сервис, который исчез.",
        "coda_is_quotable": True,
        "retell_matches_coda": True,
        "passes": True,
        "fix_hint": "",
        "summary": "кода работает",
    }
    report = evaluate_retell(_script(), llm=FakeLLM(payload))
    assert report.passes is True


def test_e6_compression_ratio_gate():
    original = _script()
    # ~22% shorter texts
    short_lines = []
    for line in original.lines:
        cut = line.text[: max(1, int(len(line.text) * 0.78))]
        short_lines.append(line.model_copy(update={"text": cut}))
    compressed = original.model_copy(update={"lines": short_lines})
    report = CompressionReport(
        script_id="s1",
        original_chars=0,
        compressed_chars=0,
        reduction_ratio=0,
        script=compressed,
        passes=False,
        summary="cut",
    )
    out = finalize_compression(report, original)
    assert 0.18 <= out.reduction_ratio <= 0.30
    assert out.passes is True


def test_e6_rejects_foreign_claim_id():
    original = _script()
    bad = original.model_copy(
        update={
            "lines": [
                original.lines[0].model_copy(update={"claim_id": "other"}),
                *original.lines[1:],
            ]
        }
    )
    report = CompressionReport(
        script_id="s1",
        original_chars=10,
        compressed_chars=8,
        reduction_ratio=0.2,
        script=bad,
        passes=True,
        summary="x",
    )
    out = finalize_compression(report, original)
    assert out.passes is False


def test_e6_compress_script_integration():
    original = _script()
    short_lines = [
        line.model_copy(update={"text": line.text[: max(1, int(len(line.text) * 0.78))]})
        for line in original.lines
    ]
    payload = {
        "script_id": "s1",
        "original_chars": 1,
        "compressed_chars": 1,
        "reduction_ratio": 0.2,
        "script": original.model_copy(update={"lines": short_lines}).model_dump(mode="json"),
        "passes": True,
        "summary": "убрал воду",
    }
    out = compress_script(original, llm=FakeLLM(payload))
    assert out.script.claim_id == original.claim_id
    assert out.reduction_ratio > 0
