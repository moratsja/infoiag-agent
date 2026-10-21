import json
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
EXTRACT_SYSTEM_PROMPT = """Extract claims from the summary.
Return only JSON: {"claims": [...]} with no markdown.
Each claim has subject, predicate, object, scope, claim_type, relevant_entities, and text.
scope is one of: individual, some, many, most, general, universal, limited.
Use universal for all/everyone/every. Use general for an unquantified group such as "Americans".
claim_type is one of: factual, ontology_relation, attitude, group, observation.
Use attitude for love, hate, enjoy, or celebrate. Use ontology_relation for a relation or a class.
Use observation for a hedged description of the posts.
relevant_entities is a list of strings. text is the sentence the claim came from.
Do not add claims that are not in the summary.
"""

class ClaimModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    subject: str
    predicate: str
    obj: str = Field(default="", alias="object")
    scope: str = "general"
    claim_type: str = "factual"
    relevant_entities: list[str] = Field(default_factory=list)
    text: str = ""

    @field_validator("scope", mode="before")
    @classmethod
    def _scope(cls, value):
        key = str(value or "").strip().lower()
        key = _SCOPE_ALIASES.get(key, key)
        return key if key in SCOPES else "general"

    @field_validator("claim_type", mode="before")
    @classmethod
    def _claim_type(cls, value):
        key = str(value or "").strip().lower().replace(" ", "_")
        key = _TYPE_ALIASES.get(key, key)
        return key if key in CLAIM_TYPES else "factual"

    @field_validator("relevant_entities", mode="before")
    @classmethod
    def _entities(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item) for item in value]

def parse_claims(payload):
    data = json.loads(_json_text(payload))
    rows = data["claims"] if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Claims payload must be a list or an object with a claims list.")
    return [ClaimModel.model_validate(row) for row in rows]

def dump_claims(claims):
    return [claim.model_dump(by_alias=True) for claim in claims]

def extract_claims(state):
    summary = state["summary"]
    claims = _claims_for_summary(summary) if summary.strip() else []
    dumped = dump_claims(claims)
    update = {
        "claims": dumped,
        "summary_sentences": split_sentences(summary),
        "trace": ["extract_claims"],
    }
    if not dumped:
        update["passed"] = False
        update["issues"] = []
        update["claim_evaluations"] = []
    return update

def _claims_for_summary(summary):
    from src.llm.model import complete

    raw = complete(EXTRACT_SYSTEM_PROMPT, f"Summary:\n{summary}")
    return parse_claims(raw)

def _json_text(payload):
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
