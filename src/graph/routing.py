def route_after_extract(state):
    # No claims means there is nothing to check.
    if not state.get("claims"):
        return "end"
    return "ontology_mapping"


def route_after_evaluate(state):
    # Rewrite once, and only when a claim is inconsistent with the ontology.
    if state["passed"] or state["revision"] >= state["max_revisions"]:
        return "end"
    return "rewrite"
