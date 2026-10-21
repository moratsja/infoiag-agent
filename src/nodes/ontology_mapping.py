import json
import re

from src.ontology.reasoner import claim_shape
from src.ontology.vocabulary import load_vocabulary

MAPPER_SYSTEM_PROMPT = """You map extracted summary claims to an ontology vocabulary.
Use only classes, object properties, and individuals from the vocabulary.
Do not invent names. Do not write SPARQL.
If a claim cannot be checked with this vocabulary, set ontology_relevant to false.
Return only JSON: {"mappings": [...]} with one object per claim, in the same order.
Each mapping is one object with claim_index, ontology_relevant, and nested subject, predicate, and object.
subject and object each have text, ontology_class, and ontology_entity.
predicate has text and ontology_property.
Use "" when a field has no match.
A class membership leaves ontology_property and the object entity empty, and puts the class in ontology_class.
A relation puts the property name in ontology_property and individuals in both ontology_entity fields.
If the claim does not fit exactly one of those shapes, set ontology_relevant to false.
The same shapes apply to every topic. Use only names from the vocabulary.
Example:
{"mappings": [
 {"claim_index": 0, "ontology_relevant": true, "subject": {"text": "Eva", "ontology_class": "", "ontology_entity": "evaPerson"}, "predicate": {"text": "is a", "ontology_property": ""}, "object": {"text": "a person", "ontology_class": "Person", "ontology_entity": ""}},
 {"claim_index": 1, "ontology_relevant": true, "subject": {"text": "bread", "ontology_class": "", "ontology_entity": "breadFood"}, "predicate": {"text": "has ingredient", "ontology_property": "hasIngredient"}, "object": {"text": "flour", "ontology_class": "", "ontology_entity": "flourIngredient"}}

]}
"""

def ontology_mapping(state):
    claims = state.get("claims") or []
    if not claims:
        return {"mapped_claims": [], "trace": ["ontology_mapping"]}
    from src.llm.model import complete

    vocabulary = load_vocabulary()
    raw = complete(
        MAPPER_SYSTEM_PROMPT,
        "\n".join(
            [
                "Ontology vocabulary:",
                json.dumps(vocabulary, ensure_ascii=False),
                "",
                "Claims:",
                json.dumps(claims, ensure_ascii=False),
            ]
        ),
    )
    return {"mapped_claims": parse_mappings(raw, len(claims), vocabulary), "trace": ["ontology_mapping"]}

def parse_mappings(payload, claim_count, vocabulary):
    data = json.loads(_json_text(payload))
    rows = data["mappings"] if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Mappings payload must be a list or an object with a mappings list.")
    classes = {row["name"] for row in vocabulary["classes"]}
    properties = {row["name"] for row in vocabulary["object_properties"]}
    individuals = {row["name"] for row in vocabulary["individuals"]}
    mappings = []
    for index in range(claim_count):
        row = rows[index] if index < len(rows) else {}
        mappings.append(_clean(index, row, classes, properties, individuals))
    return mappings

def _clean(index, row, classes, properties, individuals):
    subject = _side(row.get("subject"), classes, individuals)
    predicate = row.get("predicate") if isinstance(row.get("predicate"), dict) else {}
    obj = _side(row.get("object"), classes, individuals)
    prop = predicate.get("ontology_property") or ""
    prop = prop if prop in properties else ""
    mapping = {
        "claim_index": index,
        "ontology_relevant": False,
        "subject": subject,
        "predicate": {"text": str(predicate.get("text") or ""), "ontology_property": prop},
        "object": obj,
    }
    mapping["ontology_relevant"] = claim_shape(mapping) is not None
    return mapping

def _side(value, classes, individuals):
    side = value if isinstance(value, dict) else {}
    cls = side.get("ontology_class") or ""
    entity = side.get("ontology_entity") or ""
    return {
        "text": str(side.get("text") or ""),
        "ontology_class": cls if cls in classes else "",
        "ontology_entity": entity if entity in individuals else "",
    }

def _json_text(payload):
    stripped = payload.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n", "", stripped)
        stripped = re.sub(r"\n```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1:
        return stripped[start : end + 1]
    return stripped
