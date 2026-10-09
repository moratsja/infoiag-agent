from __future__ import annotations

from typing import Literal

from src.graph.state import AgentState


def route_after_evaluate(state: AgentState) -> Literal["rewrite", "end"]:
    # Stop if the check passed, or if the one allowed rewrite is already used.
    if state["passed"] or state["revision"] >= state["max_revisions"]:
        return "end"
    return "rewrite"
