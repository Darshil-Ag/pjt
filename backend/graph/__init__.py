"""graph/__init__.py

Lazy imports so that node-level unit tests don't trigger the LangGraph
StateGraph / SQLite checkpointer dependency chain.
"""
from __future__ import annotations

# Nodes are importable directly without pulling in the full compiled graph.
from graph.nodes import (
    context_router_node,
    retrieval_node,
    parallel_dispatch_node,
    conflict_index_node,
    route_after_conflict,
    hitl_node,
    hitl_resume_node,
    fusion_node,
    sensitivity_sweep_node,
    red_team_node,
    evaluation_logger_node,
)

__all__ = [
    # Nodes
    "context_router_node",
    "retrieval_node",
    "parallel_dispatch_node",
    "conflict_index_node",
    "route_after_conflict",
    "hitl_node",
    "hitl_resume_node",
    "fusion_node",
    "sensitivity_sweep_node",
    "red_team_node",
    "evaluation_logger_node",
    # Graph builders (imported lazily on demand)
    "build_graph",
    "get_compiled_graph",
    "create_evaluation_run",
]


def build_graph():
    """Lazy import of build_graph to avoid eager LangGraph/SQLite import."""
    from graph.graph import build_graph as _build
    return _build()


def get_compiled_graph(checkpointer=None):
    """Lazy import of get_compiled_graph."""
    from graph.graph import get_compiled_graph as _get
    return _get(checkpointer=checkpointer)


def create_evaluation_run(startup_pitch: str):
    """Lazy import of create_evaluation_run."""
    from graph.graph import create_evaluation_run as _create
    return _create(startup_pitch)

