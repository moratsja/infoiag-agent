def route_after_extract(state):
    if not state.get("claims"):
        return "end"
    return "ontology_mapping"

def route_after_evaluate(state):
    needs_rewrite = any(
        issue.get("kind") == "inconsistency"
        for issue in state.get("issues") or []
    )
    if not needs_rewrite or state["revision"] >= state["max_revisions"]:
        return "end"
    return "rewrite"
