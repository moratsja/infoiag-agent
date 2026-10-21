# Give each claim a status from the query result.
# Only CONTRADICTED is an issue. NOT_VERIFIABLE is logged and does not trigger a rewrite.

import re

from src.ontology.claim_queries import local_name, template_for_claim


def evaluate(state):
    grouped = state.get("query_results_by_claim") or []
    verdicts = []
    for index, claim in enumerate(state.get("claims") or []):
        verdicts.append(
            judge_claim(claim, _results_for(index, grouped), _template_for(index, grouped))
        )
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
        "passed": len(issues) == 0,
        "trace": ["evaluate"],
    }


def judge_claim(claim, results, template = None):
    chosen = template or template_for_claim(claim) or _template_from_results(results)
    ok_rows = [row for result in results if result["status"] == "ok" for row in result["rows"]]
    query_id = results[0]["query_id"] if results else ""
    if chosen == "recognizes_public_holiday":
        return _judge_holiday(claim, ok_rows, query_id)
    if chosen == "individual_type":
        return _judge_type(claim, ok_rows, query_id)
    if chosen == "non_participant":
        return _judge_non_participant(claim, ok_rows, query_id)
    return {
        "status": "NOT_VERIFIABLE",
        "query_id": query_id,
        "message": (
            f"The ontology has no relation for '{claim.get('subject')} {claim.get('predicate')} "
            f"{claim.get('object')}'. An empty lookup does not prove the claim false."
        ),
        "claim": claim,
    }


def _judge_holiday(claim, rows, query_id):
    holidays = {local_name(row.get("holiday", "")) for row in rows}
    about_christmas = "christmas" in holidays and _asserts_recognized_holiday(claim)
    if about_christmas:
        return _verdict(
            "SUPPORTED",
            query_id,
            "The ontology records that america recognizesPublicHoliday christmas, which matches this claim.",
            claim,
        )
    if holidays:
        shown = ", ".join(sorted(holidays))
        return _verdict(
            "CONTRADICTED",
            query_id,
            f"The ontology records recognizesPublicHoliday for {shown}, which does not match '{claim.get('object')}'.",
            claim,
        )
    return _verdict(
        "NOT_VERIFIABLE",
        query_id,
        "The holiday-recognition query returned no rows, so the claim is not established.",
        claim,
    )


def _judge_type(claim, rows, query_id):
    found = {row.get("type", "") for row in rows if row.get("type")}
    claimed = local_name(claim.get("object", ""))
    if claimed in found:
        return _verdict("SUPPORTED", query_id, f"The ontology types this individual as {claimed}.", claim)
    if found:
        shown = ", ".join(sorted(found))
        return _verdict(
            "CONTRADICTED",
            query_id,
            f"The ontology types this individual as {shown}, not as {claimed}.",
            claim,
        )
    return _verdict("NOT_VERIFIABLE", query_id, "No class assertion was returned for this individual.", claim)


def _judge_non_participant(claim, rows, query_id):
    # A hit means the ontology has a non-participant. No hit does not prove the claim.
    if rows:
        shown = ", ".join(next(iter(row.values())) for row in rows if row) or "at least one person"
        return _verdict(
            "CONTRADICTED",
            query_id,
            f"The ontology has someone who is not a Christmas participant ({shown}).",
            claim,
        )
    return _verdict(
        "NOT_VERIFIABLE",
        query_id,
        "The non-participant query returned no rows. That does not prove the claim.",
        claim,
    )


def _asserts_recognized_holiday(claim):
    blob = _claim_blob(claim)
    mentions_country = "united states" in blob or re.search(r"\bamerica\b", blob) is not None
    mentions_holiday = "public holiday" in blob or "recogn" in blob
    return "christmas" in blob and mentions_country and mentions_holiday


def _claim_blob(claim):
    return " ".join(
        [
            str(claim.get("subject", "")),
            str(claim.get("predicate", "")),
            str(claim.get("object", "")),
            str(claim.get("text", "")),
        ]
    ).lower()


def _verdict(status, query_id, message, claim):
    return {"status": status, "query_id": query_id, "message": message, "claim": claim}


def _results_for(index, grouped):
    for item in grouped:
        if item.get("claim_index") == index:
            return item.get("results") or []
    return []


def _template_for(index, grouped):
    for item in grouped:
        if item.get("claim_index") == index:
            return item.get("template")
    return None


def _template_from_results(results):
    if not results:
        return None
    query_id = results[0]["query_id"]
    if query_id == "q5_america_recognizes_christmas":
        return "recognizes_public_holiday"
    if query_id == "q1_americans_not_celebrating_christmas":
        return "non_participant"
    if str(query_id).startswith("individual_type"):
        return "individual_type"
    return None
