# Fixed SPARQL lookups. These are not OWL verdicts.
# q1 uses FILTER NOT EXISTS, which is closed-world: a missing row is not an OWL negation.
# Claim status comes from src.ontology.reasoner, which checks the mapped subject and object.

import re

from src.config import ONTOLOGY_IRI
from src.ontology.tools import run_sparql

_LOCAL_NAMES = {
    "america": "america",
    "american": "america",
    "americans": "america",
    "unitedstates": "america",
    "usa": "america",
    "christmas": "christmas",
    "publicholiday": "PublicHolidayEvent",
    "publicholidayevent": "PublicHolidayEvent",
    "sportingcompetition": "SportingCompetitionEvent",
    "sportingcompetitionevent": "SportingCompetitionEvent",
    "sport": "SportingCompetitionEvent",
    "country": "Country",
}
_QUERY_INDIVIDUALS = {"america", "christmas"}


def local_name(value):
    key = re.sub(r"[^a-z0-9]", "", value.lower())
    return _LOCAL_NAMES.get(key, value.strip())


def template_for_claim(claim):
    predicate = re.sub(r"[^a-z]", "", claim.get("predicate", "").lower())
    names = _names(claim)
    blob = f"{claim.get('predicate', '')} {claim.get('object', '')} {claim.get('text', '')}".lower()
    if ("recogn" in predicate or "public holiday" in blob) and "christmas" in names and "america" in names:
        return "recognizes_public_holiday"
    if predicate in {"type", "isa", "rdftype", "hastyp"} or "sport" in claim.get("object", "").lower():
        if "christmas" in names or "america" in names:
            return "individual_type"
    return None


def queries_for_claim(claim):
    template = template_for_claim(claim)
    return _run_template(template, claim)


def queries_for_mapping(mapping):
    # The property name comes from the mapper. Only these properties have a fixed query.
    if not mapping or not mapping.get("ontology_relevant"):
        return None, []
    prop = (mapping.get("predicate") or {}).get("ontology_property") or ""
    if prop == "recognizesPublicHoliday":
        return "recognizes_public_holiday", _run_template("recognizes_public_holiday", mapping)
    if prop in {"isParticipantOf", "hasParticipant"}:
        return "non_participant", _run_template("non_participant", mapping)
    return None, []


def _run_template(template, source):
    if template == "recognizes_public_holiday":
        return [run_sparql("q5_america_recognizes_christmas", _holiday_sparql(), "recognizesPublicHoliday")]
    if template == "non_participant":
        from src.ontology.queries import get_query

        query = get_query("q1_americans_not_celebrating_christmas")
        return [run_sparql(query.id, query.sparql, query.manchester)]
    if template == "individual_type":
        individual = _individual(source)
        if individual is None:
            return []
        return [run_sparql(f"individual_type:{individual}", _type_sparql(individual), "rdf:type")]
    return []


def _names(claim):
    values = [
        claim.get("subject", ""),
        claim.get("object", ""),
        claim.get("text", ""),
        *claim.get("relevant_entities", []),
    ]
    names = {local_name(value) for value in values if value}
    blob = " ".join(values).lower()
    if "america" in blob or "united states" in blob:
        names.add("america")
    if "christmas" in blob:
        names.add("christmas")
    return names


def _individual(claim):
    for candidate in (claim.get("subject", ""), *claim.get("relevant_entities", [])):
        name = local_name(candidate)
        if name in _QUERY_INDIVIDUALS:
            return name
    return None


def _holiday_sparql():
    return f"""PREFIX : <{ONTOLOGY_IRI}>
SELECT ?country ?holiday WHERE {{
  ?country :recognizesPublicHoliday ?holiday .
}}"""


def _type_sparql(individual):
    return f"""PREFIX : <{ONTOLOGY_IRI}>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?type WHERE {{
  :{individual} a ?type .
  FILTER(?type != owl:NamedIndividual && ?type != owl:Thing)
}}"""
