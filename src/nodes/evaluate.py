# Check the summary against the ontology.
# SUPPORTED and CONTRADICTED come from a real query hit.
# An empty result is NOT_VERIFIABLE: that does not mean the sentence is false.
# A broad attitude about Americans or everyone becomes a bias issue and can trigger a rewrite.

from __future__ import annotations

import re

from src.graph.state import AgentState, ClaimEvaluation, Issue, QueryResult
from src.ontology.claim_queries import local_name, template_for_claim


def evaluate(state: AgentState) -> dict:
    # Claims first. The keyword check below still catches phrases the claim list missed.
    grouped = state.get("query_results_by_claim") or []
    verdicts = [
        judge_claim(claim, _results_for(index, grouped), _template_for(index, grouped))
        for index, claim in enumerate(state.get("claims") or [])
    ]
    issues = issues_from_verdicts(verdicts)
    keyword_issues = find_issues(state["summary"], state.get("query_results") or [])
    if verdicts:
        issues = _merge_issues(issues, keyword_issues)
    else:
        issues = keyword_issues
    return {
        "claim_evaluations": verdicts,
        "issues": issues,
        "passed": len(issues) == 0,
        "trace": ["evaluate"],
    }


def find_issues(summary: str, query_results: list[QueryResult]) -> list[Issue]:
    issues: list[Issue] = []
    if not summary.strip():
        issues.append(
            {
                "kind": "quality",
                "query_id": "",
                "message": "The summary is empty.",
            }
        )
        return issues

    by_id = {result["query_id"]: result for result in query_results}
    issues.extend(_christmas_issues(summary, by_id.get("q1_americans_not_celebrating_christmas")))
    issues.extend(_holiday_overclaim(summary, by_id.get("q5_america_recognizes_christmas")))
    return issues


def _christmas_issues(summary: str, result: QueryResult | None) -> list[Issue]:
    if result is None or result["status"] != "ok" or not result["rows"]:
        return []
    if not _universal_christmas(summary):
        return []
    names = _labels(result["rows"])
    shown = ", ".join(names) if names else "at least one person"
    return [
        {
            "kind": "bias",
            "query_id": result["query_id"],
            "message": (
                "The summary treats Christmas celebration as true of Americans in general. "
                f"Query q1 returns people who are American citizens and not Christmas participants ({shown}). "
                "Rewrite the claim so it does not speak for all Americans."
            ),
        }
    ]


def _holiday_overclaim(summary: str, result: QueryResult | None) -> list[Issue]:
    if result is None or result["status"] != "ok" or not result["rows"]:
        return []
    if not _universal_christmas(summary):
        return []
    shown = ", ".join(value for row in result["rows"] for value in row.values() if value) or "america, christmas"
    return [
        {
            "kind": "bias",
            "query_id": result["query_id"],
            "message": (
                "The summary treats Christmas as something Americans in general love or celebrate. "
                f"Query q5 only returns a country recognizing a public holiday ({shown}). "
                "Recognition by america is not a feeling shared by every American. "
                "Rewrite the claim so it does not speak for Americans in general."
            ),
        }
    ]


def _universal_christmas(summary: str) -> bool:
    text = summary.lower()
    if re.search(r"\b(not all|not every|some|many)\s+americans\b", text):
        return False
    patterns = (
        r"\ball americans\b",
        r"\bevery american\b",
        r"\bamericans (all )?(love|loves|celebrate|celebrates)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _labels(rows: list[dict[str, str]]) -> list[str]:
    labels: list[str] = []
    for row in rows:
        if not row:
            continue
        labels.append(next(iter(row.values())))
    return labels


def mean_jaccard_by_group(summary: str, documents: list[dict[str, str]]) -> dict[str, float]:
    # Word overlap per group. This is not Equal Coverage and it does not trigger a rewrite.
    summary_tokens = _tokens(summary)
    grouped: dict[str, list[str]] = {}
    for doc in documents:
        grouped.setdefault(doc["group"], []).append(doc["text"])
    scores: dict[str, float] = {}
    for group, texts in grouped.items():
        group_tokens = _tokens(" ".join(texts))
        scores[group] = _jaccard(summary_tokens, group_tokens)
    return scores


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9']+", text.lower()) if len(token) > 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


_ATTITUDE_PREDICATES = {"love", "loves", "hate", "hates", "dislike", "dislikes", "celebrate", "celebrates"}


def judge_claim(claim: dict, results: list[QueryResult], template: str | None = None) -> ClaimEvaluation:
    # "Americans love Christmas" stays NOT_VERIFIABLE. The holiday fact does not prove a feeling.
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


def issues_from_verdicts(verdicts: list[ClaimEvaluation]) -> list[Issue]:
    issues: list[Issue] = []
    for verdict in verdicts:
        claim = verdict["claim"]
        if verdict["status"] == "CONTRADICTED":
            issues.append(
                {
                    "kind": "inconsistency",
                    "query_id": verdict["query_id"],
                    "message": verdict["message"],
                }
            )
        elif verdict["status"] == "NOT_VERIFIABLE" and _is_broad_attitude(claim):
            issues.append(
                {
                    "kind": "bias",
                    "query_id": verdict["query_id"],
                    "message": (
                        f"{verdict['message']} The tweets are the evidence for what people posted. "
                        "Rewrite this as a limited description of those posts, not as a general attitude."
                    ),
                }
            )
    return issues


def _judge_holiday(claim: dict, rows: list[dict[str, str]], query_id: str) -> ClaimEvaluation:
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


def _judge_type(claim: dict, rows: list[dict[str, str]], query_id: str) -> ClaimEvaluation:
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


def _is_broad_attitude(claim: dict) -> bool:
    # Only "Americans love Christmas" style claims. "Some posts" and one DivSumm group do not count.
    if claim.get("claim_type") == "group":
        return False
    subject = str(claim.get("subject", "")).lower()
    if re.search(r"\b(some|many|several|a few)\b", subject):
        return False
    if re.search(r"\b(white|hispanic|hisp|african-american|african american)\b", subject):
        return False
    predicate = re.sub(r"[^a-z]", "", str(claim.get("predicate", "")).lower())
    attitude = claim.get("claim_type") == "attitude" or predicate in _ATTITUDE_PREDICATES
    if not attitude:
        return False
    population = bool(re.search(r"\b(americans|everyone|everybody|people|users)\b", subject))
    if claim.get("scope") == "universal" and population:
        return True
    if claim.get("scope") == "general" and population:
        return True
    return bool(re.search(r"\b(all|every|everyone|everybody)\s+americans\b", subject))


def _asserts_recognized_holiday(claim: dict) -> bool:
    blob = _claim_blob(claim)
    mentions_country = "united states" in blob or re.search(r"\bamerica\b", blob) is not None
    mentions_holiday = "public holiday" in blob or "recogn" in blob
    return "christmas" in blob and mentions_country and mentions_holiday


def _claim_blob(claim: dict) -> str:
    return " ".join(
        [
            str(claim.get("subject", "")),
            str(claim.get("predicate", "")),
            str(claim.get("object", "")),
            str(claim.get("text", "")),
        ]
    ).lower()


def _verdict(status: str, query_id: str, message: str, claim: dict) -> ClaimEvaluation:
    return {"status": status, "query_id": query_id, "message": message, "claim": claim}  # type: ignore[return-value]


def _judge_non_participant(claim: dict, rows: list[dict[str, str]], query_id: str) -> ClaimEvaluation:
    # A person who is not a Christmas participant makes "all Americans celebrate" unsafe.
    # No such row does not prove the sentence false.
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


def _results_for(index: int, grouped: list[dict]) -> list[QueryResult]:
    for item in grouped:
        if item.get("claim_index") == index:
            return item.get("results") or []
    return []


def _template_for(index: int, grouped: list[dict]) -> str | None:
    for item in grouped:
        if item.get("claim_index") == index:
            return item.get("template")
    return None


def _template_from_results(results: list[QueryResult]) -> str | None:
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


def _merge_issues(primary: list[Issue], fallback: list[Issue]) -> list[Issue]:
    merged = list(primary)
    seen = {(item["kind"], item["query_id"]) for item in primary}
    for item in fallback:
        key = (item["kind"], item["query_id"])
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged
