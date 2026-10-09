# Agent: tweets -> summary -> claims -> ontology mapping -> fixed SPARQL -> check.
# A failed check rewrites once, then the new summary is checked again.
# The baseline graph is only the summary step.

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.config import MAX_REVISIONS, SUMMARY_SENTENCES
from src.graph.routing import route_after_evaluate
from src.graph.state import AgentState
from src.nodes.evaluate import evaluate
from src.nodes.claims import extract_claims
from src.nodes.ontology_mapping import ontology_mapping
from src.nodes.rewrite import rewrite
from src.nodes.select_query import select_query
from src.nodes.summarize import summarize


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("summarize", summarize)
    builder.add_node("extract_claims", extract_claims)
    builder.add_node("ontology_mapping", ontology_mapping)
    builder.add_node("select_query", select_query)
    builder.add_node("evaluate", evaluate)
    builder.add_node("rewrite", rewrite)

    builder.add_edge(START, "summarize")
    builder.add_edge("summarize", "extract_claims")
    builder.add_edge("extract_claims", "ontology_mapping")
    builder.add_edge("ontology_mapping", "select_query")
    builder.add_edge("select_query", "evaluate")
    builder.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"rewrite": "rewrite", "end": END},
    )
    builder.add_edge("rewrite", "extract_claims")
    return builder.compile()


def build_baseline_graph():
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
        "summary_sentences": [],
        "claims": [],
        "mapped_claims": [],
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
