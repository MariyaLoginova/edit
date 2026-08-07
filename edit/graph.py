"""LangGraph EDIT: темы→факты→вирусный ролик→E-критик→[E7]."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from edit.a2_claim_miner import mine_claims
from edit.b1_scoring import score_claims
from edit.c1_material import collect_material
from edit.c1_research_enricher import enrich_material
from edit.c2_images import collect_images
from edit.c3_soft_factcheck import soft_factcheck
from edit.d2_prose import write_prose
from edit.e1_traceability import audit_traceability
from edit.e4_openings import rewrite_openings
from edit.e_check import check_monologue
from edit.e_editor import plan_story
from edit.e_hook import write_hook
from edit.e7_ideator import (
    apply_probe_to_script,
    parse_include_decision,
    propose_idea_probe,
)
from edit.e_critic import critique_as_retention, critique_script
from edit.d2_monologue import write_monologue
from edit.f1_shotlist import build_shotlist
from edit.g1_post_analyst import analyze_rollouts, apply_weight_update
from edit.state import EditState
from edit.stubs import require_frozen_dossier, require_manual_script, resolve_selected_claim
from models import SoftFactcheckResult


def node_a2_mine(state: EditState, *, llm: Any = None) -> dict:
    return {"claims": mine_claims(state["source_map"], llm=llm)}


def node_b1_score(state: EditState) -> dict:
    claims = state.get("claims") or []
    return {"scored_claims": score_claims(claims)}


def node_b2_select_stub(state: EditState) -> dict:
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


def node_d2_prose(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    return {"script": write_prose(dossier, llm=llm)}


def node_e_editor(state: EditState, *, llm: Any = None) -> dict:
    claim = resolve_selected_claim(state.get("claims") or [], state.get("selected_claim_id"))
    primary_text = state.get("primary_text") or "\n\n".join(
        segment.text for segment in (state.get("source_map").segments if state.get("source_map") else [])
    )
    return {"story_brief": plan_story(claim, primary_text=primary_text, llm=llm)}


def node_c1_research(
    state: EditState,
    *,
    searcher: Any = None,
) -> dict:
    """C1 после E-редактора: кодовый поиск по research_queries, без LLM."""
    claim = resolve_selected_claim(state.get("claims") or [], state.get("selected_claim_id"))
    brief = state.get("story_brief")
    if brief is None:
        raise ValueError("C1 research: нет StoryBrief")
    primary_text = state.get("primary_text") or ""
    dossier = collect_material(
        claim,
        searcher=searcher,
        llm=None,
        primary_text=primary_text,
        research_queries=brief.research_queries,
    )
    return {"dossier": dossier}


def node_c1_research_enricher(state: EditState, *, llm: Any = None) -> dict:
    dossier = state.get("dossier")
    brief = state.get("story_brief")
    if dossier is None or brief is None:
        raise ValueError("C1.5: нужен dossier и StoryBrief")
    enriched, pack = enrich_material(dossier, brief, llm=llm)
    return {"dossier": enriched, "research_pack": pack}


def node_c1_freeze_primary(state: EditState) -> dict:
    """C1 без отдельного LLM: citation уже валидирована A2, E проверит текст после D2."""
    dossier = state.get("dossier")
    if dossier is None:
        raise ValueError("C1: нет dossier")
    checked = dossier.model_copy(
        update={
            "soft_factcheck": SoftFactcheckResult(
                ok=True,
                rationale="Первичный источник и цитата переданы в E-проверку.",
            )
        }
    )
    return {"dossier": checked.freeze(require_images=False)}


def node_d2_monologue(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    brief = state.get("story_brief")
    if brief is None:
        raise ValueError("D2: нет StoryBrief от E-редактора")
    hook_options = state.get("hook_options")
    return {
        "monologue": write_monologue(
            dossier,
            brief,
            hook_text=(
                hook_options.variants[0].first_line
                if hook_options is not None
                else brief.opening
            ),
            llm=llm,
        )
    }


def node_e_hook(state: EditState, *, llm: Any = None) -> dict:
    brief = state.get("story_brief")
    if brief is None:
        raise ValueError("E-hook: нет StoryBrief")
    return {"hook_options": write_hook(brief, llm=llm)}


def node_e_monologue_check(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    monologue = state.get("monologue")
    if monologue is None:
        raise ValueError("E-проверка: нет монолога D2")
    report = check_monologue(
        monologue,
        dossier,
        brief=state.get("story_brief"),
        llm=llm,
    )
    return {"monologue_check": report, "blocked_for_production": not report.passes}


def node_material_blocked(state: EditState) -> dict:
    return {"blocked_for_production": True}


def node_e1_trace(state: EditState) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    script = require_manual_script(state.get("script"))
    report = audit_traceability(script, dossier)
    return {"trace": report, "blocked_for_production": not report.passes}


def _after_e1(state: EditState) -> Literal["e_critic", "blocked"]:
    if state.get("blocked_for_production"):
        return "blocked"
    return "e_critic"


def node_e_critic(state: EditState, *, llm: Any = None, set_block: bool = False) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    script = require_manual_script(state.get("script"))
    report = critique_script(script, dossier, llm=llm)
    out: dict[str, Any] = {
        "critique": report,
        # адаптеры для кода, который ещё читает старые поля
        "retention": critique_as_retention(report),
    }
    if set_block:
        out["blocked_for_production"] = not report.passes
    return out


def node_e4_openings(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    script = require_manual_script(state.get("script"))
    retention = state.get("retention")
    if retention is None and state.get("critique") is not None:
        retention = critique_as_retention(state["critique"])
    pick = rewrite_openings(script, dossier, retention, llm=llm)
    return {"opening_pick": pick, "script": pick.script}


def node_editorial_gate(state: EditState) -> dict:
    """Прод-гейт: E1 + E-критик (если присутствуют)."""
    checks: list[bool] = []
    if state.get("trace") is not None:
        checks.append(state["trace"].passes)
    if state.get("critique") is not None:
        checks.append(state["critique"].passes)
    elif state.get("retention") is not None:
        checks.append(state["retention"].passes)
    blocked = any(ok is False for ok in checks)
    return {"blocked_for_production": blocked}


def _after_editorial_gate(state: EditState) -> Literal["e7_propose", "blocked"]:
    if state.get("blocked_for_production"):
        return "blocked"
    return "e7_propose"


def node_e7_propose(state: EditState, *, llm: Any = None) -> dict:
    dossier = require_frozen_dossier(state.get("dossier"))
    script = require_manual_script(state.get("script"))
    probe = propose_idea_probe(dossier, script, llm=llm)
    return {"idea_probe": probe, "idea_probe_included": None}


def node_e7_gate(state: EditState, *, auto_decision: bool | None = None) -> dict:
    from langgraph.types import interrupt

    probe = state.get("idea_probe")
    if probe is None:
        raise ValueError("E7 gate: нет idea_probe — сначала e7_propose")

    if auto_decision is not None:
        include = bool(auto_decision)
    else:
        resume_value = interrupt(
            {
                "type": "e7_include_probe",
                "prompt": (
                    "Включить идейный разгон в ролик? "
                    "Ответьте include/exclude или {\"include\": true|false}."
                ),
                "probe": probe.model_dump(mode="json"),
            }
        )
        include = parse_include_decision(resume_value)
    return {"idea_probe_included": include}


def node_e7_apply(state: EditState) -> dict:
    script = require_manual_script(state.get("script"))
    probe = state.get("idea_probe")
    included = state.get("idea_probe_included")
    if not included:
        return {"script": script}
    if probe is None:
        raise ValueError("E7 apply: нет idea_probe")
    return {"script": apply_probe_to_script(script, probe)}


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
    g.add_node("c3_factcheck", lambda s: node_c3_factcheck(s, llm=llm))


def build_material_graph(*, llm: Any = None, searcher: Any = None):
    g = StateGraph(EditState)
    g.add_node("c1_material", lambda s: node_c1_material(s, llm=llm, searcher=searcher))
    g.add_node("c3_factcheck", lambda s: node_c3_factcheck(s, llm=llm))
    g.add_edge(START, "c1_material")
    g.add_edge("c1_material", "c3_factcheck")
    g.add_edge("c3_factcheck", END)
    return g.compile()


def build_vertical_slice_graph(*, llm: Any = None, searcher: Any = None):
    g = StateGraph(EditState)
    g.add_node("a2_mine", lambda s: node_a2_mine(s, llm=llm))
    g.add_node("b2_select_stub", node_b2_select_stub)
    g.add_node("e_critic", lambda s: node_e_critic(s, llm=llm, set_block=True))
    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "e_critic")
    g.add_edge("e_critic", END)
    return g.compile()


def build_v2_slice_graph(*, llm: Any = None, searcher: Any = None):
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    g.add_node("d_manual_script", node_d_manual_script)
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e_critic", lambda s: node_e_critic(s, llm=llm, set_block=True))

    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "c1_material")
    g.add_edge("c1_material", "c3_factcheck")
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
        {"e_critic": "e_critic", "blocked": "e1_blocked"},
    )
    g.add_edge("e1_blocked", END)
    g.add_edge("e_critic", END)
    return g.compile()


def build_v3_slice_graph(*, llm: Any = None, searcher: Any = None):
    """C→D2→E1→E-критик (без D1/D3)."""
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    g.add_node("d2_prose", lambda s: node_d2_prose(s, llm=llm))
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e_critic", lambda s: node_e_critic(s, llm=llm, set_block=True))

    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "c1_material")
    g.add_edge("c1_material", "c3_factcheck")
    g.add_conditional_edges(
        "c3_factcheck",
        _after_c3,
        {"d_layer": "d2_prose", "blocked": "material_blocked"},
    )
    g.add_edge("material_blocked", END)
    g.add_edge("d2_prose", "e1_trace")
    g.add_conditional_edges(
        "e1_trace",
        _after_e1,
        {"e_critic": "e_critic", "blocked": "e1_blocked"},
    )
    g.add_edge("e1_blocked", END)
    g.add_edge("e_critic", END)
    return g.compile()


def build_v4_slice_graph(*, llm: Any = None, searcher: Any = None):
    """… → E1 → E-критик → E4 → gate."""
    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    g.add_node("d2_prose", lambda s: node_d2_prose(s, llm=llm))
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e_critic", lambda s: node_e_critic(s, llm=llm, set_block=False))
    g.add_node("e4_openings", lambda s: node_e4_openings(s, llm=llm))
    g.add_node("editorial_gate", node_editorial_gate)

    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b2_select_stub")
    g.add_edge("b2_select_stub", "c1_material")
    g.add_edge("c1_material", "c3_factcheck")
    g.add_conditional_edges(
        "c3_factcheck",
        _after_c3,
        {"d_layer": "d2_prose", "blocked": "material_blocked"},
    )
    g.add_edge("material_blocked", END)
    g.add_edge("d2_prose", "e1_trace")
    g.add_conditional_edges(
        "e1_trace",
        _after_e1,
        {"e_critic": "e_critic", "blocked": "e1_blocked"},
    )
    g.add_edge("e1_blocked", END)
    g.add_edge("e_critic", "e4_openings")
    g.add_edge("e4_openings", "editorial_gate")
    g.add_edge("editorial_gate", END)
    return g.compile()


def build_editorial_graph(*, llm: Any = None):
    """E-критик → E4 → gate. Вход: frozen dossier + script."""
    g = StateGraph(EditState)
    g.add_node("e_critic", lambda s: node_e_critic(s, llm=llm))
    g.add_node("e4_openings", lambda s: node_e4_openings(s, llm=llm))
    g.add_node("editorial_gate", node_editorial_gate)
    g.add_edge(START, "e_critic")
    g.add_edge("e_critic", "e4_openings")
    g.add_edge("e4_openings", "editorial_gate")
    g.add_edge("editorial_gate", END)
    return g.compile()


def build_scenario_graph(*, llm: Any = None):
    """Только D2 (озвучка + таймкоды)."""
    g = StateGraph(EditState)
    g.add_node("d2_prose", lambda s: node_d2_prose(s, llm=llm))
    g.add_edge(START, "d2_prose")
    g.add_edge("d2_prose", END)
    return g.compile()


def _add_e7_nodes(
    g: StateGraph,
    *,
    llm: Any,
    e7_auto_decision: bool | None,
) -> None:
    g.add_node("e7_propose", lambda s: node_e7_propose(s, llm=llm))
    g.add_node("e7_gate", lambda s: node_e7_gate(s, auto_decision=e7_auto_decision))
    g.add_node("e7_apply", node_e7_apply)
    g.add_node("prod_blocked", node_material_blocked)


def build_v5_slice_graph(
    *,
    llm: Any = None,
    searcher: Any = None,
    checkpointer: Any = None,
    e7_auto_decision: bool | None = None,
):
    from langgraph.checkpoint.memory import MemorySaver

    g = StateGraph(EditState)
    _add_abc_nodes(g, llm=llm, searcher=searcher)
    g.add_node("b1_score", node_b1_score)
    g.add_node("d2_prose", lambda s: node_d2_prose(s, llm=llm))
    g.add_node("material_blocked", node_material_blocked)
    g.add_node("e1_trace", node_e1_trace)
    g.add_node("e1_blocked", node_material_blocked)
    g.add_node("e_critic", lambda s: node_e_critic(s, llm=llm, set_block=False))
    g.add_node("e4_openings", lambda s: node_e4_openings(s, llm=llm))
    g.add_node("editorial_gate", node_editorial_gate)
    _add_e7_nodes(g, llm=llm, e7_auto_decision=e7_auto_decision)

    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", "b1_score")
    g.add_edge("b1_score", "b2_select_stub")
    g.add_edge("b2_select_stub", "c1_material")
    g.add_edge("c1_material", "c3_factcheck")
    g.add_conditional_edges(
        "c3_factcheck",
        _after_c3,
        {"d_layer": "d2_prose", "blocked": "material_blocked"},
    )
    g.add_edge("material_blocked", END)
    g.add_edge("d2_prose", "e1_trace")
    g.add_conditional_edges(
        "e1_trace",
        _after_e1,
        {"e_critic": "e_critic", "blocked": "e1_blocked"},
    )
    g.add_edge("e1_blocked", END)
    g.add_edge("e_critic", "e4_openings")
    g.add_edge("e4_openings", "editorial_gate")
    g.add_conditional_edges(
        "editorial_gate",
        _after_editorial_gate,
        {"e7_propose": "e7_propose", "blocked": "prod_blocked"},
    )
    g.add_edge("prod_blocked", END)
    g.add_edge("e7_propose", "e7_gate")
    g.add_edge("e7_gate", "e7_apply")
    g.add_edge("e7_apply", END)

    cp = checkpointer
    if cp is None and e7_auto_decision is None:
        cp = MemorySaver()
    return g.compile(checkpointer=cp)


def build_e7_graph(
    *,
    llm: Any = None,
    checkpointer: Any = None,
    e7_auto_decision: bool | None = None,
):
    from langgraph.checkpoint.memory import MemorySaver

    g = StateGraph(EditState)
    g.add_node("e7_propose", lambda s: node_e7_propose(s, llm=llm))
    g.add_node("e7_gate", lambda s: node_e7_gate(s, auto_decision=e7_auto_decision))
    g.add_node("e7_apply", node_e7_apply)
    g.add_edge(START, "e7_propose")
    g.add_edge("e7_propose", "e7_gate")
    g.add_edge("e7_gate", "e7_apply")
    g.add_edge("e7_apply", END)
    cp = checkpointer
    if cp is None and e7_auto_decision is None:
        cp = MemorySaver()
    return g.compile(checkpointer=cp)


def build_learning_graph(*, persist: bool = False):
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


def build_personal_story_graph(*, llm: Any = None, searcher: Any = None):
    """FIX-5: E-editor → web research → C1.5 meat → D2 → fact check."""
    g = StateGraph(EditState)
    g.add_node("e_editor", lambda s: node_e_editor(s, llm=llm))
    # C1 не получает llm: E-редактор дал запросы, код собирает подтверждения.
    g.add_node("c1_research", lambda s: node_c1_research(s, searcher=searcher))
    g.add_node("c1_research_enricher", lambda s: node_c1_research_enricher(s, llm=llm))
    g.add_node("c1_freeze_primary", node_c1_freeze_primary)
    g.add_node("e_hook", lambda s: node_e_hook(s, llm=llm))
    g.add_node("d2_monologue", lambda s: node_d2_monologue(s, llm=llm))
    g.add_node("e_monologue_check", lambda s: node_e_monologue_check(s, llm=llm))
    g.add_edge(START, "e_editor")
    g.add_edge("e_editor", "c1_research")
    g.add_edge("c1_research", "c1_research_enricher")
    g.add_edge("c1_research_enricher", "c1_freeze_primary")
    g.add_edge("c1_freeze_primary", "e_hook")
    g.add_edge("e_hook", "d2_monologue")
    g.add_edge("d2_monologue", "e_monologue_check")
    g.add_edge("e_monologue_check", END)
    return g.compile()


def build_edit_graph(
    *,
    llm: Any = None,
    searcher: Any = None,
    checkpointer: Any = None,
    e7_auto_decision: bool | None = None,
):
    # Новый продуктовый контур; E7 подключается отдельным вызовом после human review.
    return build_personal_story_graph(llm=llm, searcher=searcher)


def build_a2_only_graph(*, llm: Any = None):
    g = StateGraph(EditState)
    g.add_node("a2_mine", lambda s: node_a2_mine(s, llm=llm))
    g.add_edge(START, "a2_mine")
    g.add_edge("a2_mine", END)
    return g.compile()


def build_e2_only_graph(*, llm: Any = None):
    """Совместимость: один E-критик (нужен dossier+script)."""
    g = StateGraph(EditState)
    g.add_node("e_critic", lambda s: node_e_critic(s, llm=llm, set_block=True))
    g.add_edge(START, "e_critic")
    g.add_edge("e_critic", END)
    return g.compile()


def build_e1_only_graph():
    g = StateGraph(EditState)
    g.add_node("e1_trace", node_e1_trace)
    g.add_edge(START, "e1_trace")
    g.add_edge("e1_trace", END)
    return g.compile()
