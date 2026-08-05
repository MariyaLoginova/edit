"""Веха 0: база content-writer импортируется и собирает граф без изменений."""

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1] / "base" / "content-writer"
sys.path.insert(0, str(BASE))


@pytest.mark.skipif(
    not (BASE / "content_writer" / "__init__.py").exists(),
    reason="vendored content-writer missing",
)
def test_build_graph_compiles():
    pytest.importorskip("langgraph")
    pytest.importorskip("langchain_openai")
    pytest.importorskip("langchain_anthropic")

    from content_writer import build_graph

    graph = build_graph()
    assert graph is not None
    # CompiledStateGraph exposes nodes; callModel + generateInsights — как в апстриме
    nodes = set(graph.get_graph().nodes)
    assert "callModel" in nodes
    assert "generateInsights" in nodes
