# Run the HermiT check for each mapped claim.
# The model does not write SPARQL. One claim is not judged from another claim's row.

from src.ontology.reasoner import check_mapping


def select_query(state):
    claims = state.get("claims") or []
    mappings = state.get("mapped_claims") or []
    by_claim = []
    results = []
    for index, _claim in enumerate(claims):
        mapping = mappings[index] if index < len(mappings) else {}
        if isinstance(mapping, dict) and "claim_index" not in mapping:
            mapping = {**mapping, "claim_index": index}
        verdict = check_mapping(mapping)
        by_claim.append({
            "claim_index": index,
            "template": verdict["template"],
            "status": verdict["status"],
            "message": verdict["message"],
            "results": [],
        })
        results.append({
            "query_id": verdict["template"] or "",
            "manchester": "",
            "status": "error" if verdict["message"].startswith("Reasoner error") or "inconsistent before" in verdict["message"] else "ok",
            "detail": verdict["message"],
            "rows": [],
        })
    return {
        "query_results": results,
        "query_results_by_claim": by_claim,
        "trace": ["select_query"],
    }
