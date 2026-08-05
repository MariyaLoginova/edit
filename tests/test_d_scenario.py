from __future__ import annotations

import pytest
from pydantic import ValidationError

from edit.d1_architect import architect_beats
from edit.d2_prose import write_prose
from edit.d3_tov import apply_tov, load_tov
from models import (
    BeatList,
    BeatRole,
    Citation,
    ClaimCard,
    ClaimKind,
    Dossier,
    Scope,
    ScriptDraft,
    SoftFactcheckResult,
)
from tests.fakes import FakeLLM


def _frozen_dossier() -> Dossier:
    claim = ClaimCard(
        claim_id="lbd-maintenance-not-luxury",
        kind=ClaimKind.causal,
        claim="Маленькое чёрное взлетело как наряд без ухода",
        counter_expectation="Думают, что это про роскошь",
        visual_hint="Chanel LBD Vogue 1926",
        citation=Citation(locator="гл.2", quote="required almost no maintenance"),
        scope=Scope(period="1920s", author_or_work="Chanel"),
        source_segment_id="ch2-s1",
        confidence=0.9,
    )
    return Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes="LBD succeeded because low maintenance",
        soft_factcheck=SoftFactcheckResult(ok=True, rationale="ok"),
    ).freeze()


def _valid_beats_payload(claim_id: str = "lbd-maintenance-not-luxury") -> dict:
    return {
        "script_id": "s-lbd",
        "claim_id": claim_id,
        "duration_sec": 40.0,
        "beats": [
            {
                "beat_id": "b1",
                "t_start": 0.0,
                "t_end": 3.0,
                "role": "hook_evidence",
                "claim_id": claim_id,
                "intent": "Объект: LBD на обложке",
            },
            {
                "beat_id": "b2",
                "t_start": 3.0,
                "t_end": 10.0,
                "role": "rupture",
                "claim_id": claim_id,
                "intent": "Не роскошь, а уход",
            },
            {
                "beat_id": "b3",
                "t_start": 10.0,
                "t_end": 20.0,
                "role": "cause",
                "claim_id": claim_id,
                "intent": "Причина — отсутствие горничной / maintenance",
            },
            {
                "beat_id": "b4",
                "t_start": 20.0,
                "t_end": 30.0,
                "role": "proof",
                "claim_id": claim_id,
                "intent": "Цитата/пруф из досье",
            },
            {
                "beat_id": "b5",
                "t_start": 30.0,
                "t_end": 40.0,
                "role": "coda",
                "claim_id": claim_id,
                "intent": "Формула на уход",
            },
        ],
    }


def _script_from_beats(beats: BeatList) -> dict:
    lines = []
    for b in beats.beats:
        lines.append(
            {
                "t_start": b.t_start,
                "t_end": b.t_end,
                "text": f"Текст бита {b.role.value}",
                "claim_id": beats.claim_id,
                "beat_id": b.beat_id,
            }
        )
    return {
        "script_id": beats.script_id,
        "claim_id": beats.claim_id,
        "duration_sec": beats.duration_sec,
        "tov_applied": False,
        "lines": lines,
    }


def test_beatlist_requires_timecodes_and_roles():
    with pytest.raises(ValidationError):
        BeatList(script_id="x", claim_id="c", duration_sec=10, beats=[])
    with pytest.raises(ValidationError):
        BeatList.model_validate(
            {
                "script_id": "x",
                "claim_id": "c",
                "duration_sec": 3,
                "beats": [
                    {
                        "beat_id": "b1",
                        "t_start": 0,
                        "t_end": 3,
                        "role": "hook_evidence",
                        "claim_id": "c",
                    }
                ],
            }
        )


def test_beatlist_rejects_time_gap():
    payload = _valid_beats_payload()
    payload["beats"][2]["t_start"] = 15.0  # дыра после b2 ending 10
    with pytest.raises(ValidationError):
        BeatList.model_validate(payload)


def test_d1_architect_from_frozen_dossier():
    dossier = _frozen_dossier()
    llm = FakeLLM(_valid_beats_payload(dossier.claim_id))
    beats = architect_beats(dossier, llm=llm)
    assert beats.duration_sec == 40.0
    assert beats.beats[0].role is BeatRole.hook_evidence
    assert beats.beats[0].t_start == 0.0


def test_d1_rejects_unfrozen_dossier():
    d = _frozen_dossier()
    unfrozen = d.model_copy(update={"frozen": False, "frozen_at": None})
    with pytest.raises(ValueError, match="замороженное"):
        architect_beats(unfrozen, llm=FakeLLM(_valid_beats_payload()))


def test_d2_writes_script_grounded_in_dossier():
    dossier = _frozen_dossier()
    beats = BeatList.model_validate(_valid_beats_payload())
    llm = FakeLLM(_script_from_beats(beats))
    script = write_prose(dossier, beats, llm=llm)
    assert len(script.lines) == len(beats.beats)
    assert all(line.claim_id == dossier.claim_id for line in script.lines)


def test_d2_rejects_foreign_claim_id():
    dossier = _frozen_dossier()
    beats = BeatList.model_validate(_valid_beats_payload())
    bad = _script_from_beats(beats)
    bad["lines"][1]["claim_id"] = "other-claim"
    with pytest.raises(ValueError, match="чужим claim_id"):
        write_prose(dossier, beats, llm=FakeLLM(bad))


def test_d3_preserves_timecodes_and_sets_tov_flag():
    beats = BeatList.model_validate(_valid_beats_payload())
    script = ScriptDraft.model_validate(_script_from_beats(beats))
    rewritten = _script_from_beats(beats)
    for line in rewritten["lines"]:
        line["text"] = line["text"] + " / tov"
    llm = FakeLLM(rewritten)
    out = apply_tov(script, llm=llm, tov=load_tov())
    assert out.tov_applied is True
    assert [ (l.t_start, l.t_end, l.claim_id) for l in out.lines ] == [
        (l.t_start, l.t_end, l.claim_id) for l in script.lines
    ]
    assert all("/ tov" in l.text for l in out.lines)


def test_d3_rejects_line_count_change():
    beats = BeatList.model_validate(_valid_beats_payload())
    script = ScriptDraft.model_validate(_script_from_beats(beats))
    bad = _script_from_beats(beats)
    bad["lines"] = bad["lines"][:2]
    with pytest.raises(ValueError, match="число строк"):
        apply_tov(script, llm=FakeLLM(bad))
