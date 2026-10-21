# Read the HermiT status stored for each claim.
# A rewrite issue is created only for CONTRADICTED.
# passed means every claim is SUPPORTED, not merely that nothing was contradicted.

def evaluate(state):
    claims = state.get("claims") or []
    grouped = state.get("query_results_by_claim") or []
    verdicts = []
    for index, claim in enumerate(claims):
        item = _item_for(index, grouped)
        status = item.get("status") or "NOT_VERIFIABLE"
        if status not in {"SUPPORTED", "CONTRADICTED", "NOT_VERIFIABLE"}:
            status = "NOT_VERIFIABLE"
        message = item.get("message") or "No ontology check was stored for this claim."
        verdicts.append({
            "status": status,
            "query_id": item.get("template") or "",
            "message": message,
            "claim": claim,
        })
    issues = [
        {
            "kind": "inconsistency",
            "query_id": verdict["query_id"],
            "message": verdict["message"],
        }
        for verdict in verdicts
        if verdict["status"] == "CONTRADICTED"
    ]
    return {
        "claim_evaluations": verdicts,
        "issues": issues,
        "passed": bool(verdicts) and all(_is_supported(verdict) for verdict in verdicts),
        "trace": ["evaluate"],
    }


def _is_supported(verdict):
    if verdict["status"] != "SUPPORTED":
        return False
    message = verdict["message"]
    if message.startswith("Reasoner error") or "inconsistent before" in message:
        return False
    return True


def _item_for(index, grouped):
    for item in grouped:
        if item.get("claim_index") == index:
            return item
    return {}
