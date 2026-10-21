# trace is appended. Other fields are replaced.

import operator
from typing import Annotated, Literal, TypedDict

class Issue(TypedDict):
    kind: str
    query_id: str
    message: str

class QueryResult(TypedDict):
    query_id: str
    manchester: str
    status: Literal["ok", "error"]
    detail: str
    rows: list[dict[str, str]]

class ClaimEvaluation(TypedDict):
    status: Literal["SUPPORTED", "CONTRADICTED", "NOT_VERIFIABLE"]
    query_id: str
    message: str
    claim: dict

class AgentState(TypedDict):
    topic: str
    documents: list[dict[str, str]]
    user_prompt: str
    prompt_id: str
    k: int
    mode: Literal["agent", "baseline"]
    summary_sentences: list[str]
    claims: list[dict]
    mapped_claims: list[dict]
    summary: str
    query_results: list[QueryResult]
    query_results_by_claim: list[dict]
    claim_evaluations: list[ClaimEvaluation]
    issues: list[Issue]
    revision: int
    max_revisions: int
    passed: bool
    trace: Annotated[list[str], operator.add]
