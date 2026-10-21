# Pick a fixed SPARQL query from the mapping and run it.
# A claim with no known property is left unchecked. No query is invented.

from src.ontology.claim_queries import queries_for_mapping


def select_query(state):
    claims = state.get("claims") or []
    mappings = state.get("mapped_claims") or []
    by_claim = []
    results = []
    for index, _claim in enumerate(claims):
        mapping = mappings[index] if index < len(mappings) else {}
        template, query_results = queries_for_mapping(mapping)
        by_claim.append({"claim_index": index, "template": template, "results": query_results})
        results.extend(query_results)
    return {
        "query_results": _merge_results(results),
        "query_results_by_claim": by_claim,
        "trace": ["select_query"],
    }


def _merge_results(results):
    merged = []
    seen = set()
    for item in results:
        if item["query_id"] in seen:
            continue
        merged.append(item)
        seen.add(item["query_id"])
    return merged
