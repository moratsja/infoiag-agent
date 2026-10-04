"""Conditional edges for the evaluate node."""

from __future__ import annotations

from typing import Literal

from src.graph.state import AgentState


def route_after_evaluate(state: AgentState) -> Literal["rewrite", "end"]:
    """Decide whether the summary still has to be rewritten.

    Rewrite is chosen only when the ontology check found issues and the
    rewrite budget is not used up. The rewrite node connects back to
    ``extract_claims``, so the revised text is extracted, queried, and
    evaluated again. Otherwise the graph ends, including when issues remain
    after the last allowed rewrite.
    """
    if state["passed"] or state["revision"] >= state["max_revisions"]:
        return "end"
    return "rewrite"
