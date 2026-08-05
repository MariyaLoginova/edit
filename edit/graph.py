"""LangGraph-скелет вехи 1: A2 → (stub select) → E2.

Слои B/C/D между ними — ручные: выбранный claim_id и ScriptDraft приходят в state.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from edit.a2_claim_miner import mine_claims
from edit.e2_retention_critic import critique_retention
from edit.state import EditState
from edit.stubs import require_manual_script, select_claim


def node_a2_mine(state: EditState, *, llm: Any = None) -> dict:
    source_map = state["source_map"]
    cards = mine_claims(source_map, llm=llm)
    return {"claims": cards}


def node_b2_select_stub(state: EditState) -> dict:
    select_claim(state.get("claims") or [], state.get("selected_claim_id"))
    return {}


def node_e2_critique(state: EditState, *, llm: Any = None) -> dict:
    script = require_manual_script(state.get("script"))
    report = critique_retention(script, llm=llm)
    return {
        "retention": report,
        "blocked_for_production": not report.passes,
    }


def build_vertical_slice_graph(*, llm: Any = None):
    """A2 → B2-stub → E2. Для полного прогона нужны source_map + script (+ опц. selected_claim_id)."""

    def a2(state: EditState) -> dict:
        return node_a2_mine(state, llm=llm)

    def e2(state: EditState) -> dict:
        return node_e2_critique(state, llm=llm)

    g = StateGraph(EditState)
    g.add_node("a2_mine", a2)
    g.add_node("b2_select_stub", node_b2_select_stub)
    g.add_node("e2_critique", e2)
    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "e2_critique")
    g.add_edge("e2_critique", END)
    return g.compile()


def build_edit_graph(*, llm: Any = None):
    """Алиас: пока единственный собранный граф — вертикальный срез вехи 1."""
    return build_vertical_slice_graph(llm=llm)


def build_a2_only_graph(*, llm: Any = None):
    def a2(state: EditState) -> dict:
        return node_a2_mine(state, llm=llm)

    g = StateGraph(EditState)
    g.add_node("a2_mine", a2)
    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", END)
    return g.compile()


def build_e2_only_graph(*, llm: Any = None):
    def e2(state: EditState) -> dict:
        return node_e2_critique(state, llm=llm)

    g = StateGraph(EditState)
    g.add_node("e2_critique", e2)
    g.add_edge(START, "e2_critique")
    g.add_edge("e2_critique", END)
    return g.compile()
