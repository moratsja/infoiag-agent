"""LangGraph wiring for the ontology agent and the one-shot baseline.

Agent execution:

    START → extract_input → retrieve_ontology → summarize
          → extract_claims → query_ontology → evaluate
    evaluate → rewrite → extract_claims   when issues remain and revision < max
    evaluate → END                        when the check passes, or the rewrite budget is spent

``retrieve_ontology`` loads background facts before the first summary.
``query_ontology`` runs the fixed SPARQL templates selected from the claims.
The model does not choose the queries.
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.config import MAX_REVISIONS, SUMMARY_SENTENCES
from src.graph.routing import route_after_evaluate
from src.graph.state import AgentState
from src.nodes.evaluate import evaluate
from src.nodes.claims import extract_claims
from src.nodes.extract import extract_input
from src.nodes.ontology import query_ontology, retrieve_ontology
from src.nodes.rewrite import rewrite
from src.nodes.summarize import summarize


def build_graph():
    """Compile the ontology-guided agent."""
    builder = StateGraph(AgentState)
    builder.add_node("extract_input", extract_input)
    builder.add_node("retrieve_ontology", retrieve_ontology)
    builder.add_node("summarize", summarize)
    builder.add_node("extract_claims", extract_claims)
    builder.add_node("query_ontology", query_ontology)
    builder.add_node("evaluate", evaluate)
    builder.add_node("rewrite", rewrite)

    builder.add_edge(START, "extract_input")
    builder.add_edge("extract_input", "retrieve_ontology")
    builder.add_edge("retrieve_ontology", "summarize")
    builder.add_edge("summarize", "extract_claims")
    builder.add_edge("extract_claims", "query_ontology")
    builder.add_edge("query_ontology", "evaluate")
    builder.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"rewrite": "rewrite", "end": END},
    )
    builder.add_edge("rewrite", "extract_claims")
    return builder.compile()


def build_baseline_graph():
    """Compile a one-shot summarizer that does not load the ontology."""
    builder = StateGraph(AgentState)
    builder.add_node("summarize", summarize)
    builder.add_edge(START, "summarize")
    builder.add_edge("summarize", END)
    return builder.compile()


def initial_state(
    documents: list[dict[str, str]],
    user_prompt: str,
    topic: str,
    prompt_id: str = "",
    k: int = SUMMARY_SENTENCES,
    mode: Literal["agent", "baseline"] = "agent",
    max_revisions: int = MAX_REVISIONS,
) -> AgentState:
    return {
        "topic": topic,
        "documents": documents,
        "user_prompt": user_prompt,
        "prompt_id": prompt_id,
        "k": k,
        "mode": mode,
        "extracted_input": {},
        "summary_sentences": [],
        "claims": [],
        "ontology_context": [],
        "summary": "",
        "query_results": [],
        "query_results_by_claim": [],
        "claim_evaluations": [],
        "issues": [],
        "revision": 0,
        "max_revisions": max_revisions,
        "passed": False,
        "trace": [],
    }


def draw_mermaid(mode: str = "agent") -> str:
    graph = build_baseline_graph() if mode == "baseline" else build_graph()
    return graph.get_graph().draw_mermaid()
