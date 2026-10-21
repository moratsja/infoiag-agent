def route_after_extract(state):
    # No claims means there is nothing to check.
    if not state.get("claims"):
        return "end"
    return "ontology_mapping"


def route_after_evaluate(state):
    # Rewrite only for a real contradiction, and only while a revision is left.
    # passed is not used here: not-verifiable claims do not start a rewrite.
    contradicted = any(issue.get("kind") == "inconsistency" for issue in state.get("issues") or [])
    if not contradicted or state["revision"] >= state["max_revisions"]:
        return "end"
    return "rewrite"
