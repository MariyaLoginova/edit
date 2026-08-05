"""EDIT — редакционный конвейер (LangGraph-узлы).

Импортируйте узлы/графы из подмодулей напрямую, например:
`from edit.graph import build_v2_slice_graph` — чтобы не плодить циклы.
"""

__all__ = [
    "build_a2_only_graph",
    "build_e1_only_graph",
    "build_e2_only_graph",
    "build_edit_graph",
    "build_material_graph",
    "build_v2_slice_graph",
    "build_vertical_slice_graph",
]


def __getattr__(name: str):
    if name in __all__:
        from edit import graph as _graph

        return getattr(_graph, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
