from __future__ import annotations

import uuid

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from edit.e7_ideator import (
    apply_probe_to_script,
    looks_like_hypothesis,
    parse_include_decision,
    propose_idea_probe,
    validate_idea_probe,
)
from edit.graph import build_e7_graph
from models import (
    Citation,
    ClaimKind,
    ContrastPair,
    Dossier,
    IdeaProbe,
    ProbeRegister,
    Scope,
    ScriptDraft,
    ScriptLine,
)
from tests.claim_factory import make_claim, make_frozen_dossier
from tests.fakes import FakeLLM


def _dossier() -> Dossier:
    claim = make_claim(
        claim_id="bild-lilli-barbie-prototype",
        kind=ClaimKind.origin,
        claim="Bild-Lilli стала прототипом Барби",
        counter_expectation="Думают, что Барби придумали с нуля в США",
        visual_hint="Bild-Lilli doll, 1955 German comic",
        object_anchor="Bild-Lilli",
        contrast_pair=ContrastPair(
            state_a="американская Барби как «новинка»",
            state_b="немецкая Bild-Lilli из комикса",
            shift="узнаваемое старое маскируется под новый бренд",
        ),
        mechanism_term="узнавание-вместо-новизны",
        mechanism_explain="Покупатель цепляется на форму, которую уже видел в другом контексте.",
        citation=Citation(locator="гл.1", quote="Lilli was the prototype for Barbie"),
        scope=Scope(period="1950s", region="Germany", author_or_work="Bild-Lilli"),
        source_segment_id="s1",
        confidence=0.9,
    )
    return make_frozen_dossier(claim, material_notes="prototype link")


def _script() -> ScriptDraft:
    return ScriptDraft(
        script_id="s1",
        claim_id="bild-lilli-barbie-prototype",
        duration_sec=30,
        lines=[
            ScriptLine(t_start=0, t_end=6, text="Не Барби придумали с нуля.", claim_id="bild-lilli-barbie-prototype"),
            ScriptLine(t_start=6, t_end=18, text="Прототипом была Bild-Lilli.", claim_id="bild-lilli-barbie-prototype"),
            ScriptLine(t_start=18, t_end=24, text="Правило живёт в сегодняшних релизах.", claim_id="bild-lilli-barbie-prototype"),
            ScriptLine(t_start=24, t_end=30, text="Формула: новое часто маскирует узнаваемое старое.", claim_id="bild-lilli-barbie-prototype"),
        ],
    )


def _probe_payload() -> dict:
    return {
        "anchor_claim_id": "bild-lilli-barbie-prototype",
        "register": "optic",
        "probe_text": (
            "Что если читать переиздание старого (сигареты, помада, бельё) "
            "как приём захвата внимания через узнавание?"
        ),
        "voiced_marker": "а если посмотреть так…",
        "generation_brief": None,
        "proposed": True,
    }


def test_hypothesis_heuristic():
    assert looks_like_hypothesis("Что если это приём?")
    assert not looks_like_hypothesis("Лили была феминистской иконой в 1955 году.")


def test_validate_rejects_non_hypothesis():
    probe = IdeaProbe(
        anchor_claim_id="bild-lilli-barbie-prototype",
        register=ProbeRegister.optic,
        probe_text="Лили была феминистской иконой.",
        voiced_marker="а если посмотреть так…",
    )
    with pytest.raises(ValueError, match="гипотез"):
        validate_idea_probe(probe, _dossier())


def test_propose_and_apply_inserts_before_coda():
    dossier = _dossier()
    script = _script()
    probe = propose_idea_probe(dossier, script, llm=FakeLLM(_probe_payload()))
    assert probe.proposed is True
    assert probe.anchor_claim_id == dossier.claim_id
    out = apply_probe_to_script(script, probe)
    assert len(out.lines) == len(script.lines) + 1
    assert out.lines[-1].text.startswith("Формула:")
    assert out.lines[-2].claim_id is None
    assert "а если посмотреть" in out.lines[-2].text.lower()


def test_parse_include_decision():
    assert parse_include_decision("include") is True
    assert parse_include_decision({"include": False}) is False
    assert parse_include_decision("нет") is False


def test_e7_graph_auto_include():
    graph = build_e7_graph(llm=FakeLLM(_probe_payload()), e7_auto_decision=True)
    out = graph.invoke({"dossier": _dossier(), "script": _script()})
    assert out["idea_probe_included"] is True
    assert any(line.beat_id == "e7_probe" for line in out["script"].lines)


def _pending_interrupts(graph, thread) -> tuple:
    """В LangGraph 0.2 invoke глушит GraphInterrupt — смотрим checkpoint."""
    snap = graph.get_state(thread)
    assert snap.next, "ожидали паузу на e7_gate"
    interrupts = tuple(i for t in snap.tasks for i in (t.interrupts or ()))
    assert interrupts, "ожидали __interrupt__ с IdeaProbe"
    return interrupts


def test_e7_graph_interrupt_and_resume_exclude():
    graph = build_e7_graph(
        llm=FakeLLM(_probe_payload()),
        checkpointer=MemorySaver(),
        e7_auto_decision=None,
    )
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    graph.invoke({"dossier": _dossier(), "script": _script()}, config=thread)
    interrupts = _pending_interrupts(graph, thread)
    assert interrupts[0].value["type"] == "e7_include_probe"
    assert "probe" in interrupts[0].value
    out = graph.invoke(Command(resume="exclude"), config=thread)
    assert out["idea_probe_included"] is False
    assert all(line.beat_id != "e7_probe" for line in out["script"].lines)


def test_e7_graph_interrupt_and_resume_include():
    graph = build_e7_graph(
        llm=FakeLLM(_probe_payload()),
        checkpointer=MemorySaver(),
    )
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    # stream явно отдаёт __interrupt__
    chunks = list(
        graph.stream({"dossier": _dossier(), "script": _script()}, config=thread)
    )
    assert any("__interrupt__" in c for c in chunks)
    out = graph.invoke(Command(resume={"include": True}), config=thread)
    assert out["idea_probe_included"] is True
    assert any("что если" in line.text.lower() for line in out["script"].lines)
