"""Map a structured claim to a fixed SPARQL template.

The model does not write SPARQL. Python picks a template from the predicate
and the entities, then the ontology tool runs that template.
"""

from __future__ import annotations

import re

from src.config import ONTOLOGY_IRI
from src.graph.state import QueryResult
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
    "film": "Film",
    "netflix": "netflixService",
    "netflixservice": "netflixService",
    "thenotebook": "theNotebookFilm",
    "thenotebookfilm": "theNotebookFilm",
}
_QUERY_INDIVIDUALS = {"america", "christmas", "netflixService", "theNotebookFilm"}


def local_name(value: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", value.lower())
    return _LOCAL_NAMES.get(key, value.strip())


def template_for_claim(claim: dict) -> str | None:
    """Return a template id, or None when no ontology relation matches the claim."""
    predicate = re.sub(r"[^a-z]", "", claim.get("predicate", "").lower())
    names = _names(claim)
    blob = f"{claim.get('predicate', '')} {claim.get('object', '')} {claim.get('text', '')}".lower()
    if ("recogn" in predicate or "public holiday" in blob) and "christmas" in names and "america" in names:
        return "recognizes_public_holiday"
    if predicate in {"type", "isa", "rdftype", "hastyp"} or "sport" in claim.get("object", "").lower():
        if "christmas" in names or "america" in names:
            return "individual_type"
    if predicate in {"offerscontent", "offers"} and ("netflix" in names or "netflixService" in names):
        return "netflix_offers"
    return None


def queries_for_claim(claim: dict) -> list[QueryResult]:
    template = template_for_claim(claim)
    if template == "recognizes_public_holiday":
        return [run_sparql("recognizes_public_holiday", _holiday_sparql(), "recognizesPublicHoliday")]
    if template == "individual_type":
        individual = _individual(claim)
        if individual is None:
            return []
        return [run_sparql(f"individual_type:{individual}", _type_sparql(individual), "rdf:type")]
    if template == "netflix_offers":
        return [run_sparql("netflix_offers", _netflix_sparql(), "offersContent")]
    return []


def _names(claim: dict) -> set[str]:
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


def _individual(claim: dict) -> str | None:
    for candidate in (claim.get("subject", ""), *claim.get("relevant_entities", [])):
        name = local_name(candidate)
        if name in _QUERY_INDIVIDUALS:
            return name
    return None


def _holiday_sparql() -> str:
    return f"""PREFIX : <{ONTOLOGY_IRI}>
SELECT ?country ?holiday WHERE {{
  ?country :recognizesPublicHoliday ?holiday .
}}"""


def _type_sparql(individual: str) -> str:
    return f"""PREFIX : <{ONTOLOGY_IRI}>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?type WHERE {{
  :{individual} a ?type .
  FILTER(?type != owl:NamedIndividual && ?type != owl:Thing)
}}"""


def _netflix_sparql() -> str:
    return f"""PREFIX : <{ONTOLOGY_IRI}>
SELECT ?content ?genre WHERE {{
  :netflixService :offersContent ?content .
  OPTIONAL {{ ?content :hasGenre ?genre . }}
}}"""
