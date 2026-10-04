"""Check a summary against ontology query results.

``find_issues`` is the evaluation function the assignment asks for: it reads
the query results and the summary, and it does not call the language model.
An empty successful query is not treated as a contradiction, because the
ontology is open-world. A query error is reported on the result itself and
does not become a rewrite issue.
"""

from __future__ import annotations

import re

from src.graph.state import AgentState, ClaimEvaluation, Issue, QueryResult
from src.ontology.claim_queries import local_name, template_for_claim

_FACILITY_CITY = re.compile(
    r"\b[Ff]acilit(?:y|ies)\s+in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
)
_STOP_CITY = {"the", "a", "an", "its", "their", "this", "that"}


def evaluate(state: AgentState) -> dict:
    """Judge extracted claims, then keep the keyword check as a fallback."""
    grouped = state.get("query_results_by_claim") or []
    verdicts = [
        judge_claim(claim, _results_for(index, grouped))
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
    """Return ontology-backed problems in ``summary``."""
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
    issues.extend(
        _netflix_polarity_issues(
            summary,
            by_id.get("q2_positive_netflix_reviews"),
            by_id.get("q4_netflix_offered_content"),
        )
    )
    issues.extend(_facility_issues(summary, by_id.get("q3_netflix_cities")))
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


def _netflix_polarity_issues(
    summary: str,
    reviews: QueryResult | None,
    offered: QueryResult | None,
) -> list[Issue]:
    if not _universal_dislike(summary):
        return []
    if reviews is not None and reviews["status"] == "ok" and reviews["rows"]:
        shown = ", ".join(_labels(reviews["rows"])) or "at least one review"
        return [
            {
                "kind": "coverage",
                "query_id": reviews["query_id"],
                "message": (
                    "The summary presents dislike of Netflix as universal. "
                    f"Query q2 returns positive Netflix reviews ({shown}). "
                    "Keep the negative points that are in the posts, and include the positive view as a differing opinion."
                ),
            }
        ]
    if offered is not None and offered["status"] == "ok" and offered["rows"]:
        shown = ", ".join(_labels(offered["rows"])) or "theNotebookFilm"
        return [
            {
                "kind": "coverage",
                "query_id": offered["query_id"],
                "message": (
                    "The summary presents dislike of Netflix as universal. "
                    f"Query q4 returns content the service offers ({shown}). "
                    "Keep the complaints that are in the posts, and do not write that everyone dislikes Netflix."
                ),
            }
        ]
    return []


def _facility_issues(summary: str, result: QueryResult | None) -> list[Issue]:
    if result is None or result["status"] != "ok" or not result["rows"]:
        return []
    known = {label.casefold() for label in _labels(result["rows"])}
    issues: list[Issue] = []
    for city in _facility_cities(summary):
        if city.casefold() not in known:
            known_text = ", ".join(sorted(_labels(result["rows"])))
            issues.append(
                {
                    "kind": "inconsistency",
                    "query_id": result["query_id"],
                    "message": (
                        f"The summary places a Netflix facility in {city}, which is not among "
                        f"the cities returned by query q3 ({known_text}). "
                        "Remove that place claim or limit it to a city the ontology returns."
                    ),
                }
            )
    return issues


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


def _universal_dislike(summary: str) -> bool:
    text = summary.lower()
    if re.search(r"\b(not everyone|some people|others like|some (users|reviewers|people) like)\b", text):
        return False
    patterns = (
        r"\b(everyone|everybody)\s+(hates|hate|dislikes|dislike)\b",
        r"\ball (people|reviewers|users|customers)\s+(hate|hates|dislike|dislikes)\b",
        r"\bno one (likes|enjoys)\b",
        r"\buniversally disliked\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _facility_cities(summary: str) -> list[str]:
    cities: list[str] = []
    for match in _FACILITY_CITY.finditer(summary):
        city = match.group(1).strip()
        first = city.split()[0].casefold()
        if first in _STOP_CITY:
            continue
        cities.append(city)
    return cities


def _labels(rows: list[dict[str, str]]) -> list[str]:
    labels: list[str] = []
    for row in rows:
        if not row:
            continue
        labels.append(next(iter(row.values())))
    return labels


def mean_jaccard_by_group(summary: str, documents: list[dict[str, str]]) -> dict[str, float]:
    """Lexical overlap between the summary and each group's tweets.

    This is the optional similarity check from the assignment, using token
    Jaccard instead of cosine similarity. It is not the Equal Coverage metric.
    """
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


_BROAD_SCOPES = {"general", "universal"}
_ATTITUDE_PREDICATES = {"love", "loves", "hate", "hates", "dislike", "dislikes", "celebrate", "celebrates"}


def judge_claim(claim: dict, results: list[QueryResult]) -> ClaimEvaluation:
    """Classify one claim as supported, contradicted, or not verifiable.

    An empty result does not make the claim false. Attitude claims such as
    "Americans love Christmas" have no ontology relation, so they stay
    NOT_VERIFIABLE even when america recognizes christmas as a holiday.
    """
    template = template_for_claim(claim)
    ok_rows = [row for result in results if result["status"] == "ok" for row in result["rows"]]
    query_id = results[0]["query_id"] if results else ""
    if template == "recognizes_public_holiday":
        return _judge_holiday(claim, ok_rows, query_id)
    if template == "individual_type":
        return _judge_type(claim, ok_rows, query_id)
    if template == "netflix_offers":
        return _judge_netflix(claim, ok_rows, query_id)
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


def _judge_netflix(claim: dict, rows: list[dict[str, str]], query_id: str) -> ClaimEvaluation:
    titles = {row.get("content", "") for row in rows if row.get("content")}
    if titles:
        shown = ", ".join(sorted(titles))
        return _verdict(
            "SUPPORTED",
            query_id,
            f"The ontology records that netflixService offers {shown}. That does not establish a universal dislike.",
            claim,
        )
    return _verdict("NOT_VERIFIABLE", query_id, "The ontology returned no offered Netflix content.", claim)


def _is_broad_attitude(claim: dict) -> bool:
    """Flag an attitude only when it speaks for Americans, everyone, or all people."""
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


def _results_for(index: int, grouped: list[dict]) -> list[QueryResult]:
    for item in grouped:
        if item.get("claim_index") == index:
            return item.get("results") or []
    return []


def _merge_issues(primary: list[Issue], fallback: list[Issue]) -> list[Issue]:
    merged = list(primary)
    seen = {(item["kind"], item["query_id"]) for item in primary}
    for item in fallback:
        key = (item["kind"], item["query_id"])
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged
