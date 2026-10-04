"""Ontology tool nodes.

Tools available to both nodes:
- ``run_queries_for_text`` runs the Intermediate Report 1 queries selected
  for the topic and the text just extracted.
- ``list_classes`` lists class names. The pipeline does not call it on every
  run; use it from the notebook when checking that the OWL file loaded.

``retrieve_ontology`` runs before the first summary and fills ``ontology_context``.
``query_ontology`` runs on the summary text and fills ``query_results``,
which the evaluator reads. The LLM does not choose whether these tools run.
"""

from __future__ import annotations

from src.graph.state import AgentState
from src.ontology.claim_queries import queries_for_claim
from src.ontology.tools import run_queries_for_text


def retrieve_ontology(state: AgentState) -> dict:
    text = state["extracted_input"].get("text", "")
    return {
        "ontology_context": run_queries_for_text(state["topic"], text),
        "trace": ["retrieve_ontology"],
    }


def query_ontology(state: AgentState) -> dict:
    """Run fixed topic queries and the SPARQL templates selected from each claim."""
    text = state["summary"] or "\n".join(state["summary_sentences"])
    topic_results = run_queries_for_text(state["topic"], f"{state['user_prompt']}\n{text}")
    by_claim: list[dict] = []
    claim_results = []
    for index, claim in enumerate(state.get("claims") or []):
        results = queries_for_claim(claim)
        by_claim.append({"claim_index": index, "results": results})
        claim_results.extend(results)
    return {
        "query_results": _merge_results(topic_results, claim_results),
        "query_results_by_claim": by_claim,
        "trace": ["query_ontology"],
    }


def _merge_results(left: list, right: list) -> list:
    merged = list(left)
    seen = {item["query_id"] for item in left}
    for item in right:
        if item["query_id"] not in seen:
            merged.append(item)
            seen.add(item["query_id"])
    return merged
