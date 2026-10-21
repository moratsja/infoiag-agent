def route_after_extract(state):
    # No claims means there is nothing to check.
    if not state.get("claims"):
        return "end"
    return "ontology_mapping"


def route_after_evaluate(state):
    # Rewrite only for an ontology contradiction, while a revision is left.
    # A NOT_VERIFIABLE claim does not start a rewrite by itself.
    needs_rewrite = any(
        issue.get("kind") == "inconsistency"
        for issue in state.get("issues") or []
    )
    if not needs_rewrite or state["revision"] >= state["max_revisions"]:
        return "end"
    return "rewrite"
