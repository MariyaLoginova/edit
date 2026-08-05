from __future__ import annotations

import pytest
from pydantic import ValidationError

from edit.d1_architect import architect_beats
from edit.d2_prose import write_prose
from edit.d3_tov import apply_tov, load_tov
from models import (
    BeatList,
    BeatRole,
    Dossier,
    ImageBuckets,
    ImageCandidate,
    ScriptDraft,
    SoftFactcheckResult,
    WebConfirmation,
)
from tests.claim_factory import make_claim
from tests.fakes import FakeLLM


def _img(url: str, state: str, query: str) -> ImageCandidate:
    return ImageCandidate(
        url=url,
        title=query,
        description=query,
        query=query,
        soft_match=True,
        for_state=state,  # type: ignore[arg-type]
    )


def _frozen_dossier() -> Dossier:
    claim = make_claim()
    pair = claim.contrast_pair
    return Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes="LBD succeeded because low maintenance",
        web_confirmations=[
            WebConfirmation(url="https://ex.com", title="t", snippet="maintenance", query="q")
        ],
        image_candidates=ImageBuckets(
            for_state_a=[_img(f"https://a/{i}.jpg", "a", pair.state_a) for i in range(3)],
            for_state_b=[_img(f"https://b/{i}.jpg", "b", pair.state_b) for i in range(3)],
            search_status="ok",
        ),
        soft_factcheck=SoftFactcheckResult(ok=True, rationale="ok"),
    ).freeze()


def _valid_beats_payload(claim_id: str = "lbd-maintenance-not-luxury") -> dict:
    return {
        "script_id": "s-lbd",
        "claim_id": claim_id,
        "duration_sec": 45.0,
        "beats": [
            {
                "beat_id": "b1",
                "t_start": 0.0,
                "t_end": 3.0,
                "role": "hook_evidence",
                "claim_id": claim_id,
                "intent": "object_anchor: LBD на обложке",
            },
            {
                "beat_id": "b2",
                "t_start": 3.0,
                "t_end": 10.0,
                "role": "false_explanation",
                "claim_id": claim_id,
                "intent": "кажется — роскошь",
            },
            {
                "beat_id": "b3",
                "t_start": 10.0,
                "t_end": 26.0,
                "role": "contrast_ab",
                "claim_id": claim_id,
                "intent": "A/B: пастель салона → чёрное прямое",
            },
            {
                "beat_id": "b4",
                "t_start": 26.0,
                "t_end": 38.0,
                "role": "mechanism",
                "claim_id": claim_id,
                "intent": "механизм сервис-вместо-статуса",
            },
            {
                "beat_id": "b5",
                "t_start": 38.0,
                "t_end": 45.0,
                "role": "coda",
                "claim_id": claim_id,
                "intent": "формула",
            },
        ],
    }


def _script_from_beats(beats: BeatList, claim=None) -> dict:
    claim = claim or make_claim()
    texts = {
        "hook_evidence": f"На экране {claim.object_anchor} — little black dress с обложки.",
        "false_explanation": "Кажется, little black dress про роскошь и статус.",
        "contrast_ab": (
            f"Сначала {claim.contrast_pair.state_a}, потом {claim.contrast_pair.state_b}: "
            f"{claim.contrast_pair.shift}."
        ),
        "mechanism": (
            f"Механизм «{claim.mechanism_term}»: {claim.mechanism_explain} "
            f"для {claim.object_anchor}."
        ),
        "coda": f"Формула: {claim.object_anchor} работает как сервис дня, не как витрина.",
    }
    lines = []
    for b in beats.beats:
        lines.append(
            {
                "t_start": b.t_start,
                "t_end": b.t_end,
                "text": texts[b.role.value],
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


def test_beatlist_rejects_early_mechanism():
    payload = _valid_beats_payload()
    payload["beats"][3]["t_start"] = 12.0
    payload["beats"][3]["t_end"] = 20.0
    payload["beats"][2]["t_end"] = 12.0
    payload["beats"][4]["t_start"] = 20.0
    with pytest.raises(ValidationError, match="mechanism слишком рано"):
        BeatList.model_validate(payload)


def test_beatlist_rejects_time_gap():
    payload = _valid_beats_payload()
    payload["beats"][2]["t_start"] = 15.0
    with pytest.raises(ValidationError):
        BeatList.model_validate(payload)


def test_d1_architect_from_frozen_dossier():
    dossier = _frozen_dossier()
    llm = FakeLLM(_valid_beats_payload(dossier.claim_id))
    beats = architect_beats(dossier, llm=llm)
    assert beats.duration_sec == 45.0
    assert beats.beats[0].role is BeatRole.hook_evidence
    assert {b.role for b in beats.beats} >= {
        BeatRole.contrast_ab,
        BeatRole.mechanism,
        BeatRole.coda,
    }


def test_d1_rejects_unfrozen_dossier():
    d = _frozen_dossier()
    unfrozen = d.model_copy(update={"frozen": False, "frozen_at": None})
    with pytest.raises(ValueError, match="замороженное"):
        architect_beats(unfrozen, llm=FakeLLM(_valid_beats_payload()))


def test_d2_writes_script_grounded_in_dossier():
    dossier = _frozen_dossier()
    beats = BeatList.model_validate(_valid_beats_payload())
    llm = FakeLLM(_script_from_beats(beats, dossier.claim))
    script = write_prose(dossier, beats, llm=llm)
    assert len(script.lines) == len(beats.beats)
    assert all(line.claim_id == dossier.claim_id for line in script.lines)


def test_d2_rejects_stop_phrase():
    dossier = _frozen_dossier()
    beats = BeatList.model_validate(_valid_beats_payload())
    bad = _script_from_beats(beats, dossier.claim)
    bad["lines"][0]["text"] = "Странно, но little black dress просто милый."
    with pytest.raises(ValueError, match="стоп-фраза"):
        write_prose(dossier, beats, llm=FakeLLM(bad))


def test_d2_rejects_foreign_claim_id():
    dossier = _frozen_dossier()
    beats = BeatList.model_validate(_valid_beats_payload())
    bad = _script_from_beats(beats, dossier.claim)
    bad["lines"][1]["claim_id"] = "other-claim"
    with pytest.raises(ValueError, match="чужим claim_id"):
        write_prose(dossier, beats, llm=FakeLLM(bad))


def test_d3_preserves_timecodes_and_sets_tov_flag():
    dossier = _frozen_dossier()
    beats = BeatList.model_validate(_valid_beats_payload())
    script = ScriptDraft.model_validate(_script_from_beats(beats, dossier.claim))
    rewritten = _script_from_beats(beats, dossier.claim)
    for line in rewritten["lines"]:
        line["text"] = line["text"] + " / tov"
    llm = FakeLLM(rewritten)
    out = apply_tov(script, llm=llm, tov=load_tov())
    assert out.tov_applied is True
    assert [(l.t_start, l.t_end, l.claim_id) for l in out.lines] == [
        (l.t_start, l.t_end, l.claim_id) for l in script.lines
    ]


def test_d3_rejects_line_count_change():
    dossier = _frozen_dossier()
    beats = BeatList.model_validate(_valid_beats_payload())
    script = ScriptDraft.model_validate(_script_from_beats(beats, dossier.claim))
    bad = _script_from_beats(beats, dossier.claim)
    bad["lines"] = bad["lines"][:2]
    with pytest.raises(ValueError, match="число строк"):
        apply_tov(script, llm=FakeLLM(bad))
