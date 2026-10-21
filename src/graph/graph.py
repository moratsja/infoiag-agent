from langgraph.graph import END, START, StateGraph

from src.config import MAX_REVISIONS, SUMMARY_SENTENCES
from src.graph.routing import route_after_evaluate, route_after_extract
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
    builder.add_conditional_edges(
        "extract_claims",
        route_after_extract,
        {"ontology_mapping": "ontology_mapping", "end": END},
    )
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
    documents,
    user_prompt,
    topic,
    prompt_id = "",
    k = SUMMARY_SENTENCES,
    mode = "agent",
    max_revisions = MAX_REVISIONS,

):
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

def draw_mermaid(mode = "agent"):
    graph = build_baseline_graph() if mode == "baseline" else build_graph()
    return graph.get_graph().draw_mermaid()
