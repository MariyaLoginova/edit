"""LangGraph: вехи 1–3 (A2, C, D1–D3, E1–E2)."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from edit.a2_claim_miner import mine_claims
from edit.c1_material import collect_material
from edit.c2_images import collect_images
from edit.c3_soft_factcheck import soft_factcheck
from edit.d1_architect import architect_beats
from edit.d2_prose import write_prose
from edit.d3_tov import apply_tov
from edit.e1_traceability import audit_traceability
from edit.e2_retention_critic import critique_retention
from edit.state import EditState
from edit.stubs import require_frozen_dossier, require_manual_script, resolve_selected_claim


def node_a2_mine(state: EditState, *, llm: Any = None) -> dict:
    return {"claims": mine_claims(state["source_map"], llm=llm)}


def node_b2_select_stub(state: EditState) -> dict:
    resolve_selected_claim(state.get("claims") or [], state.get("selected_claim_id"))
    return {}


def node_c1_material(
    state: EditState,
    *,
    llm: Any = None,
    searcher: Any = None,
) -> dict:
    claim = resolve_selected_claim(state.get("claims") or [], state.get("selected_claim_id"))
    dossier = collect_material(
        claim, searcher=searcher, llm=llm, existing=state.get("dossier")
    )
    return {"dossier": dossier}


def node_c2_images(state: EditState, *, searcher: Any = None) -> dict:
    dossier = state.get("dossier")
    if dossier is None:
        raise ValueError("C2: нет dossier после C1")
    return {"dossier": collect_images(dossier, searcher=searcher)}


def node_c3_factcheck(state: EditState, *, llm: Any = None) -> dict:
    dossier = state.get("dossier")
    if dossier is None:
        raise ValueError("C3: нет dossier")
    return {"dossier": soft_factcheck(dossier, llm=llm, auto_freeze=True)}


def _after_c3(state: EditState) -> Literal["d_layer", "blocked"]:
    dossier = state.get("dossier")
    if dossier is None or not dossier.frozen:
        return "blocked"
    return "d_layer"


def node_d_manual_script(state: EditState) -> dict:
    """Заглушка D для вехи 2: ручной ScriptDraft."""
    require_frozen_dossier(state.get("dossier"))
    require_manual_script(state.get("script"))
    return {}


def node_d1_architect(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    return {"beats": architect_beats(dossier, llm=llm)}


def node_d2_prose(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    beats = state.get("beats")
    if beats is None:
        raise ValueError("D2: нет BeatList после D1")
    return {"script": write_prose(dossier, beats, llm=llm)}


def node_d3_tov(state: EditState, *, llm: Any = None) -> dict:
    script = state.get("script")
    if script is None:
        raise ValueError("D3: нет ScriptDraft после D2")
    return {"script": apply_tov(script, llm=llm)}


def node_material_blocked(state: EditState) -> dict:
    return {"blocked_for_production": True}


def node_e1_trace(state: EditState) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    script = require_manual_script(state.get("script"))
    report = audit_traceability(script, dossier)
    return {"trace": report, "blocked_for_production": not report.passes}


def _after_e1(state: EditState) -> Literal["e2_critique", "blocked"]:
    if state.get("blocked_for_production"):
        return "blocked"
    return "e2_critique"


def node_e2_critique(state: EditState, *, llm: Any = None) -> dict:
    script = require_manual_script(state.get("script"))
    report = critique_retention(script, llm=llm)
    return {
        "retention": report,
        "blocked_for_production": not report.passes,
    }


def _add_abc_nodes(g: StateGraph, *, llm: Any, searcher: Any) -> None:
    g.add_node("a2_mine", lambda s: node_a2_mine(s, llm=llm))
    g.add_node("b2_select_stub", node_b2_select_stub)
    g.add_node("c1_material", lambda s: node_c1_material(s, llm=llm, searcher=searcher))
    g.add_node("c2_images", lambda s: node_c2_images(s, searcher=searcher))
    g.add_node("c3_factcheck", lambda s: node_c3_factcheck(s, llm=llm))


def build_material_graph(*, llm: Any = None, searcher: Any = None):
    g = StateGraph(EditState)
    g.add_node("c1_material", lambda s: node_c1_material(s, llm=llm, searcher=searcher))
    g.add_node("c2_images", lambda s: node_c2_images(s, searcher=searcher))
    g.add_node("c3_factcheck", lambda s: node_c3_factcheck(s, llm=llm))
    g.add_edge(START, "c1_material")
    g.add_edge("c1_material", "c2_images")
    g.add_edge("c2_images", "c3_factcheck")
    g.add_edge("c3_factcheck", END)
    return g.compile()


def build_vertical_slice_graph(*, llm: Any = None, searcher: Any = None):
    """Веха 1: A2 → B2-stub → E2."""
    g = StateGraph(EditState)
    g.add_node("a2_mine", lambda s: node_a2_mine(s, llm=llm))
    g.add_node("b2_select_stub", node_b2_select_stub)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm))
    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "e2_critique")
    g.add_edge("e2_critique", END)
    return g.compile()


def build_v2_slice_graph(*, llm: Any = None, searcher: Any = None):
    """Веха 2: … → C3 → D-stub(manual) → E1 → E2."""
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    g.add_node("d_manual_script", node_d_manual_script)
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm))

    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "c1_material")
    g.add_edge("c1_material", "c2_images")
    g.add_edge("c2_images", "c3_factcheck")
    g.add_conditional_edges(
        "c3_factcheck",
        lambda s: "d_manual_script" if (s.get("dossier") and s["dossier"].frozen) else "blocked",
        {"d_manual_script": "d_manual_script", "blocked": "material_blocked"},
    )
    g.add_edge("material_blocked", END)
    g.add_edge("d_manual_script", "e1_trace")
    g.add_conditional_edges(
        "e1_trace",
        _after_e1,
        {"e2_critique": "e2_critique", "blocked": "e1_blocked"},
    )
    g.add_edge("e1_blocked", END)
    g.add_edge("e2_critique", END)
    return g.compile()


def build_v3_slice_graph(*, llm: Any = None, searcher: Any = None):
    """Веха 3: … → C3 → D1 → D2 → D3 → E1 → E2."""
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    g.add_node("d1_architect", lambda s: node_d1_architect(s, llm=llm))
    g.add_node("d2_prose", lambda s: node_d2_prose(s, llm=llm))
    g.add_node("d3_tov", lambda s: node_d3_tov(s, llm=llm))
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm))

    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "c1_material")
    g.add_edge("c1_material", "c2_images")
    g.add_edge("c2_images", "c3_factcheck")
    g.add_conditional_edges(
        "c3_factcheck",
        _after_c3,
        {"d_layer": "d1_architect", "blocked": "material_blocked"},
    )
    g.add_edge("material_blocked", END)
    g.add_edge("d1_architect", "d2_prose")
    g.add_edge("d2_prose", "d3_tov")
    g.add_edge("d3_tov", "e1_trace")
    g.add_conditional_edges(
        "e1_trace",
        _after_e1,
        {"e2_critique": "e2_critique", "blocked": "e1_blocked"},
    )
    g.add_edge("e1_blocked", END)
    g.add_edge("e2_critique", END)
    return g.compile()


def build_scenario_graph(*, llm: Any = None):
    """Только D1→D2→D3. Вход: frozen dossier."""
    g = StateGraph(EditState)
    g.add_node("d1_architect", lambda s: node_d1_architect(s, llm=llm))
    g.add_node("d2_prose", lambda s: node_d2_prose(s, llm=llm))
    g.add_node("d3_tov", lambda s: node_d3_tov(s, llm=llm))
    g.add_edge(START, "d1_architect")
    g.add_edge("d1_architect", "d2_prose")
    g.add_edge("d2_prose", "d3_tov")
    g.add_edge("d3_tov", END)
    return g.compile()


def build_edit_graph(*, llm: Any = None, searcher: Any = None):
    """Актуальный полный срез — веха 3."""
    return build_v3_slice_graph(llm=llm, searcher=searcher)


def build_a2_only_graph(*, llm: Any = None):
    g = StateGraph(EditState)
    g.add_node("a2_mine", lambda s: node_a2_mine(s, llm=llm))
    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", END)
    return g.compile()


def build_e2_only_graph(*, llm: Any = None):
    g = StateGraph(EditState)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm))
    g.add_edge(START, "e2_critique")
    g.add_edge("e2_critique", END)
    return g.compile()


def build_e1_only_graph():
    g = StateGraph(EditState)
    g.add_node("e1_trace", node_e1_trace)
    g.add_edge(START, "e1_trace")
    g.add_edge("e1_trace", END)
    return g.compile()
