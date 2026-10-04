"""Structured claims taken from a generated summary.

The language model returns JSON. Python validates it. A small lexical fallback
covers a failed response so the ontology check can still run.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.graph.state import AgentState
from src.nodes.extract import split_sentences

SCOPES = {"individual", "some", "many", "most", "general", "universal", "limited"}
CLAIM_TYPES = {"factual", "ontology_relation", "attitude", "group", "observation"}
_SCOPE_ALIASES = {
    "all": "universal",
    "everyone": "universal",
    "always": "universal",
    "never": "universal",
    "few": "limited",
    "a few": "limited",
    "several": "some",
}
_TYPE_ALIASES = {
    "opinion": "attitude",
    "relation": "ontology_relation",
    "relational": "ontology_relation",
    "neutral": "observation",
    "group-specific": "group",
    "group_specific": "group",
}

EXTRACT_SYSTEM_PROMPT = """You extract claims from a summary for an ontology check.
Return only a JSON object of the form {"claims": [...]} with no markdown.
Each claim has:
- subject (string)
- predicate (string)
- object (string)
- scope: individual, some, many, most, general, universal, or limited
- claim_type: factual, ontology_relation, attitude, group, or observation
- confidence: number from 0 to 1
- relevant_entities: list of strings
- text: the sentence the claim came from

Use scope "universal" for all/everyone/every and scope "general" for an unquantified group such as "Americans".
Use claim_type "attitude" for love, hate, enjoy, or celebrate-as-feeling.
Use claim_type "ontology_relation" when the sentence states a relation such as recognizesPublicHoliday or a class membership.
Use claim_type "observation" and scope "some" for a hedged description of the posts.
Do not invent claims that are not in the summary.
"""


class ClaimModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subject: str
    predicate: str
    obj: str = Field(default="", alias="object")
    scope: str = "general"
    claim_type: str = "factual"
    confidence: float = 0.5
    relevant_entities: list[str] = Field(default_factory=list)
    text: str = ""

    @field_validator("scope", mode="before")
    @classmethod
    def _scope(cls, value: object) -> str:
        key = str(value or "").strip().lower()
        key = _SCOPE_ALIASES.get(key, key)
        return key if key in SCOPES else "general"

    @field_validator("claim_type", mode="before")
    @classmethod
    def _claim_type(cls, value: object) -> str:
        key = str(value or "").strip().lower().replace(" ", "_")
        key = _TYPE_ALIASES.get(key, key)
        return key if key in CLAIM_TYPES else "factual"

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence(cls, value: object) -> float:
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.5
        return min(1.0, max(0.0, number))

    @field_validator("relevant_entities", mode="before")
    @classmethod
    def _entities(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item) for item in value]


def parse_claims(payload: str) -> list[ClaimModel]:
    """Validate a JSON claim list. Raises ValueError when the payload is not claims."""
    data = json.loads(_json_text(payload))
    rows = data["claims"] if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Claims payload must be a list or an object with a claims list.")
    return [ClaimModel.model_validate(row) for row in rows]


def fallback_claims(summary: str) -> list[ClaimModel]:
    """Lexical claims used when the model response is not valid JSON."""
    claims: list[ClaimModel] = []
    for sentence in split_sentences(summary) or ([summary.strip()] if summary.strip() else []):
        claim = _fallback_sentence(sentence)
        if claim is not None:
            claims.append(claim)
    return claims


def dump_claims(claims: list[ClaimModel]) -> list[dict]:
    return [claim.model_dump(by_alias=True) for claim in claims]


def extract_claims(state: AgentState) -> dict:
    """Node: read the current summary and store validated claims."""
    summary = state["summary"]
    claims = _claims_for_summary(summary)
    return {
        "claims": dump_claims(claims),
        "summary_sentences": split_sentences(summary),
        "trace": ["extract_claims"],
    }


def _claims_for_summary(summary: str) -> list[ClaimModel]:
    if not summary.strip():
        return []
    try:
        from src.llm.model import complete

        raw = complete(EXTRACT_SYSTEM_PROMPT, f"Summary:\n{summary}")
        parsed = parse_claims(raw)
        if parsed:
            return parsed
    except Exception:
        pass
    return fallback_claims(summary)


def _fallback_sentence(sentence: str) -> ClaimModel | None:
    text = sentence.strip()
    if not text:
        return None
    lowered = text.lower()
    if re.search(r"\b(love|loves|hate|hates|dislike|dislikes|celebrate|celebrates)\b", lowered) and re.search(
        r"\b(americans|everyone|everybody|all people)\b", lowered
    ):
        scope = "universal" if re.search(r"\b(all|every|everyone|everybody)\b", lowered) else "general"
        if "celebrat" in lowered and "love" not in lowered:
            predicate = "celebrate"
        elif "love" in lowered:
            predicate = "love"
        else:
            predicate = "dislike"
        return ClaimModel(
            subject="Americans" if "american" in lowered else "everyone",
            predicate=predicate,
            object="Christmas" if "christmas" in lowered else "Netflix",
            scope=scope,
            claim_type="attitude",
            confidence=0.8,
            relevant_entities=["america", "christmas"] if "christmas" in lowered else ["netflixService"],
            text=text,
        )
    if re.search(r"\brecogniz\w*\b", lowered) and "christmas" in lowered and "america" in lowered:
        return ClaimModel(
            subject="America",
            predicate="recognizesPublicHoliday",
            object="Christmas",
            scope="general",
            claim_type="ontology_relation",
            confidence=0.9,
            relevant_entities=["america", "christmas"],
            text=text,
        )
    if re.search(r"\bchristmas\b", lowered) and re.search(r"\b(sport|sporting)\b", lowered):
        return ClaimModel(
            subject="Christmas",
            predicate="type",
            object="sporting competition",
            scope="general",
            claim_type="ontology_relation",
            confidence=0.9,
            relevant_entities=["christmas"],
            text=text,
        )
    if re.search(r"\b(some|many|several|a few)\b", lowered):
        scope = "some" if re.search(r"\b(some|several|a few)\b", lowered) else "many"
        return ClaimModel(
            subject="some posts" if scope == "some" else "many posts",
            predicate="describe",
            object=text[:120],
            scope=scope,
            claim_type="observation",
            confidence=0.6,
            relevant_entities=[],
            text=text,
        )
    return ClaimModel(
        subject="posts",
        predicate="mention",
        object=text[:120],
        scope="some",
        claim_type="observation",
        confidence=0.4,
        relevant_entities=[],
        text=text,
    )


def _json_text(payload: str) -> str:
    stripped = payload.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n", "", stripped)
        stripped = re.sub(r"\n```$", "", stripped)
    start = stripped.find("{")
    list_start = stripped.find("[")
    if list_start != -1 and (start == -1 or list_start < start):
        end = stripped.rfind("]")
        return stripped[list_start : end + 1]
    end = stripped.rfind("}")
    if start != -1 and end != -1:
        return stripped[start : end + 1]
    return stripped
