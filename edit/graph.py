"""LangGraph: вехи 1–5 (добыча → скоринг → материал → сценарий → редактура → F1/G1)."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from edit.a2_claim_miner import mine_claims
from edit.b1_scoring import score_claims
from edit.c1_material import collect_material
from edit.c2_images import collect_images
from edit.c3_soft_factcheck import soft_factcheck
from edit.d1_architect import architect_beats
from edit.d2_prose import write_prose
from edit.d3_tov import apply_tov
from edit.e1_traceability import audit_traceability
from edit.e2_retention_critic import critique_retention
from edit.e3_red_critic import critique_content
from edit.e4_openings import rewrite_openings
from edit.e5_retell import evaluate_retell
from edit.e6_compress import compress_script
from edit.f1_shotlist import build_shotlist
from edit.g1_post_analyst import analyze_rollouts, apply_weight_update
from edit.state import EditState
from edit.stubs import require_frozen_dossier, require_manual_script, resolve_selected_claim


def node_a2_mine(state: EditState, *, llm: Any = None) -> dict:
    return {"claims": mine_claims(state["source_map"], llm=llm)}


def node_b1_score(state: EditState) -> dict:
    claims = state.get("claims") or []
    return {"scored_claims": score_claims(claims)}


def node_b2_select_stub(state: EditState) -> dict:
    # предпочитаем ранжированный список B1, если есть
    ranked = state.get("scored_claims") or []
    pool = [s.claim for s in ranked] if ranked else (state.get("claims") or [])
    resolve_selected_claim(pool, state.get("selected_claim_id"))
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


def node_e2_critique(state: EditState, *, llm: Any = None, set_block: bool = False) -> dict:
    script = require_manual_script(state.get("script"))
    report = critique_retention(script, llm=llm)
    out: dict[str, Any] = {"retention": report}
    # v1–v3: E2 сразу влияет на blocked; v4 — только диагностика, гейт в конце
    if set_block:
        out["blocked_for_production"] = not report.passes
    return out


def node_e3_red(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    script = require_manual_script(state.get("script"))
    return {"red_critique": critique_content(script, dossier, llm=llm)}


def node_e4_openings(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    script = require_manual_script(state.get("script"))
    pick = rewrite_openings(script, dossier, state.get("retention"), llm=llm)
    return {"opening_pick": pick, "script": pick.script}


def node_e5_retell(state: EditState, *, llm: Any = None) -> dict:
    script = require_manual_script(state.get("script"))
    return {"retell": evaluate_retell(script, llm=llm)}


def node_e6_compress(state: EditState, *, llm: Any = None) -> dict:
    script = require_manual_script(state.get("script"))
    report = compress_script(script, state.get("retention"), llm=llm)
    return {"compression": report, "script": report.script}


def node_editorial_gate(state: EditState) -> dict:
    """Финальный прод-гейт: учитывает только присутствующие отчёты E1/E2/E3/E5."""
    checks: list[bool] = []
    if state.get("trace") is not None:
        checks.append(state["trace"].passes)
    if state.get("retention") is not None:
        checks.append(state["retention"].passes)
    if state.get("red_critique") is not None:
        checks.append(state["red_critique"].passes)
    if state.get("retell") is not None:
        checks.append(state["retell"].passes)
    blocked = any(ok is False for ok in checks)
    return {"blocked_for_production": blocked}


def _after_editorial_gate(state: EditState) -> Literal["f1_shots", "blocked"]:
    if state.get("blocked_for_production"):
        return "blocked"
    return "f1_shots"


def node_f1_shots(state: EditState, *, searcher: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    script = require_manual_script(state.get("script"))
    return {"shot_list": build_shotlist(script, dossier, searcher=searcher)}


def node_g1_learn(state: EditState, *, persist: bool = False) -> dict:
    metrics = state.get("rollout_metrics") or []
    update = analyze_rollouts(list(metrics))
    apply_weight_update(update, persist=persist)
    return {"weight_update": update}



def _add_abc_nodes(g: StateGraph, *, llm: Any, searcher: Any) -> None:
    g.add_node("a2_mine", lambda s: node_a2_mine(s, llm=llm))
    g.add_node("b2_select_stub", node_b2_select_stub)
    g.add_node("c1_material", lambda s: node_c1_material(s, llm=llm, searcher=searcher))
    g.add_node("c2_images", lambda s: node_c2_images(s, searcher=searcher))
    g.add_node("c3_factcheck", lambda s: node_c3_factcheck(s, llm=llm))


def _add_d_nodes(g: StateGraph, *, llm: Any) -> None:
    g.add_node("d1_architect", lambda s: node_d1_architect(s, llm=llm))
    g.add_node("d2_prose", lambda s: node_d2_prose(s, llm=llm))
    g.add_node("d3_tov", lambda s: node_d3_tov(s, llm=llm))


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
    g = StateGraph(EditState)
    g.add_node("a2_mine", lambda s: node_a2_mine(s, llm=llm))
    g.add_node("b2_select_stub", node_b2_select_stub)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm, set_block=True))
    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "e2_critique")
    g.add_edge("e2_critique", END)
    return g.compile()


def build_v2_slice_graph(*, llm: Any = None, searcher: Any = None):
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    g.add_node("d_manual_script", node_d_manual_script)
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm, set_block=True))

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
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    _add_d_nodes(g, llm=llm)
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm, set_block=True))

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


def build_v4_slice_graph(*, llm: Any = None, searcher: Any = None):
    """Веха 4: … → E1 → E2 → E3 → E4 → E5 → E6 → gate."""
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    _add_d_nodes(g, llm=llm)
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm, set_block=False))
    g.add_node("e3_red", lambda s: node_e3_red(s, llm=llm))
    g.add_node("e4_openings", lambda s: node_e4_openings(s, llm=llm))
    g.add_node("e5_retell", lambda s: node_e5_retell(s, llm=llm))
    g.add_node("e6_compress", lambda s: node_e6_compress(s, llm=llm))
    g.add_node("editorial_gate", node_editorial_gate)

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
    g.add_edge("e2_critique", "e3_red")
    g.add_edge("e3_red", "e4_openings")
    g.add_edge("e4_openings", "e5_retell")
    g.add_edge("e5_retell", "e6_compress")
    g.add_edge("e6_compress", "editorial_gate")
    g.add_edge("editorial_gate", END)
    return g.compile()


def build_editorial_graph(*, llm: Any = None):
    """Только E2→E6. Вход: frozen dossier + script."""
    g = StateGraph(EditState)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm))
    g.add_node("e3_red", lambda s: node_e3_red(s, llm=llm))
    g.add_node("e4_openings", lambda s: node_e4_openings(s, llm=llm))
    g.add_node("e5_retell", lambda s: node_e5_retell(s, llm=llm))
    g.add_node("e6_compress", lambda s: node_e6_compress(s, llm=llm))
    g.add_node("editorial_gate", node_editorial_gate)
    g.add_edge(START, "e2_critique")
    g.add_edge("e2_critique", "e3_red")
    g.add_edge("e3_red", "e4_openings")
    g.add_edge("e4_openings", "e5_retell")
    g.add_edge("e5_retell", "e6_compress")
    g.add_edge("e6_compress", "editorial_gate")
    g.add_edge("editorial_gate", END)
    return g.compile()


def build_scenario_graph(*, llm: Any = None):
    g = StateGraph(EditState)
    _add_d_nodes(g, llm=llm)
    g.add_edge(START, "d1_architect")
    g.add_edge("d1_architect", "d2_prose")
    g.add_edge("d2_prose", "d3_tov")
    g.add_edge("d3_tov", END)
    return g.compile()


def build_v5_slice_graph(*, llm: Any = None, searcher: Any = None):
    """Веха 5: A2→B1→B2→C→D→E→gate→F1. G1 — отдельный learning-граф."""
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    _add_d_nodes(g, llm=llm)
    g.add_node("b1_score", node_b1_score)
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm, set_block=False))
    g.add_node("e3_red", lambda s: node_e3_red(s, llm=llm))
    g.add_node("e4_openings", lambda s: node_e4_openings(s, llm=llm))
    g.add_node("e5_retell", lambda s: node_e5_retell(s, llm=llm))
    g.add_node("e6_compress", lambda s: node_e6_compress(s, llm=llm))
    g.add_node("editorial_gate", node_editorial_gate)
    g.add_node("f1_shots", lambda s: node_f1_shots(s, searcher=searcher))
    g.add_node("prod_blocked", node_material_blocked)

    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b1_score")
    g.add_edge("b1_score", "b2_select_stub")
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
    g.add_edge("e2_critique", "e3_red")
    g.add_edge("e3_red", "e4_openings")
    g.add_edge("e4_openings", "e5_retell")
    g.add_edge("e5_retell", "e6_compress")
    g.add_edge("e6_compress", "editorial_gate")
    g.add_conditional_edges(
        "editorial_gate",
        _after_editorial_gate,
        {"f1_shots": "f1_shots", "blocked": "prod_blocked"},
    )
    g.add_edge("prod_blocked", END)
    g.add_edge("f1_shots", END)
    return g.compile()


def build_learning_graph(*, persist: bool = False):
    """G1 offline: rollout_metrics → weight_update (+ опционально persist YAML)."""
    g = StateGraph(EditState)
    g.add_node("g1_learn", lambda s: node_g1_learn(s, persist=persist))
    g.add_edge(START, "g1_learn")
    g.add_edge("g1_learn", END)
    return g.compile()


def build_f1_only_graph(*, searcher: Any = None):
    g = StateGraph(EditState)
    g.add_node("f1_shots", lambda s: node_f1_shots(s, searcher=searcher))
    g.add_edge(START, "f1_shots")
    g.add_edge("f1_shots", END)
    return g.compile()


def build_edit_graph(*, llm: Any = None, searcher: Any = None):
    """Актуальный полный срез — веха 5."""
    return build_v5_slice_graph(llm=llm, searcher=searcher)


def build_a2_only_graph(*, llm: Any = None):
    g = StateGraph(EditState)
    g.add_node("a2_mine", lambda s: node_a2_mine(s, llm=llm))
    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", END)
    return g.compile()


def build_e2_only_graph(*, llm: Any = None):
    g = StateGraph(EditState)
    g.add_node("e2_critique", lambda s: node_e2_critique(s, llm=llm, set_block=True))
    g.add_edge(START, "e2_critique")
    g.add_edge("e2_critique", END)
    return g.compile()


def build_e1_only_graph():
    g = StateGraph(EditState)
    g.add_node("e1_trace", node_e1_trace)
    g.add_edge(START, "e1_trace")
    g.add_edge("e1_trace", END)
    return g.compile()
