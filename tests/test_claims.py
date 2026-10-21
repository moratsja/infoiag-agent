from src.config import MAX_REVISIONS
from src.graph.graph import initial_state
from src.graph.routing import route_after_evaluate
from src.nodes.claims import parse_claims
from src.nodes.evaluate import evaluate
from src.ontology.reasoner import check_mapping
from src.ontology.tools import run_sparql


def test_parse_claims_accepts_structured_json():
    payload = """
    {"claims": [{
      "subject": "Americans",
      "predicate": "love",
      "object": "Christmas",
      "scope": "all",
      "claim_type": "attitude",
      "relevant_entities": ["America", "christmas"]
    }]}
    """
    claim = parse_claims(payload)[0].model_dump(by_alias=True)
    assert claim["scope"] == "universal"
    assert claim["object"] == "Christmas"
    assert claim["claim_type"] == "attitude"
    assert "confidence" not in claim


def test_love_claim_is_not_verifiable_from_the_holiday_fact():
    verdict = check_mapping({
        "subject": {"text": "Americans", "ontology_class": "", "ontology_entity": ""},
        "predicate": {"text": "love", "ontology_property": ""},
        "object": {"text": "Christmas", "ontology_class": "", "ontology_entity": "christmas"},
    })
    assert verdict["status"] == "NOT_VERIFIABLE"


def test_love_claim_is_logged_but_does_not_rewrite():
    state = initial_state(documents=[], user_prompt="why Americans love Christmas", topic="Christmas", max_revisions=1)
    state["summary"] = "Americans love Christmas."
    state["claims"] = [
        {
            "subject": "Americans",
            "predicate": "love",
            "object": "Christmas",
            "scope": "general",
            "claim_type": "attitude",
            "text": state["summary"],
            "relevant_entities": ["america", "christmas"],
        }
    ]
    state["query_results"] = []
    state["query_results_by_claim"] = [{"claim_index": 0, "results": []}]
    checked = evaluate(state)
    assert checked["claim_evaluations"][0]["status"] == "NOT_VERIFIABLE"
    assert checked["passed"] is False
    assert checked["issues"] == []
    assert route_after_evaluate({**state, **checked}) == "end"
    assert MAX_REVISIONS == 1


def test_many_posts_from_americans_does_not_rewrite():
    claim = {
        "subject": "Many posts from Americans",
        "predicate": "reflect enjoyment",
        "object": "Christmas",
        "scope": "general",
        "claim_type": "attitude",
        "text": "Many posts from Americans reflect enjoyment of Christmas through gift-giving.",
        "relevant_entities": ["america", "christmas"],
    }
    state = initial_state(documents=[], user_prompt="", topic="Christmas")
    state["summary"] = claim["text"]
    state["claims"] = [claim]
    state["query_results"] = []
    state["query_results_by_claim"] = [{"claim_index": 0, "results": []}]
    checked = evaluate(state)
    assert checked["passed"] is False
    assert checked["issues"] == []
    assert route_after_evaluate({**state, **checked}) == "end"


def test_group_specific_enthusiasm_is_not_a_broad_claim():
    claim = {
        "subject": "White and Hispanic individuals",
        "predicate": "show enthusiasm for celebrating",
        "object": "Christmas",
        "scope": "general",
        "claim_type": "attitude",
        "relevant_entities": ["christmas"],
    }
    state = initial_state(documents=[], user_prompt="", topic="Christmas")
    state["summary"] = "Some White and Hispanic posts describe gifts."
    state["claims"] = [claim]
    state["query_results"] = []
    state["query_results_by_claim"] = [{"claim_index": 0, "results": []}]
    checked = evaluate(state)
    assert checked["claim_evaluations"][0]["status"] == "NOT_VERIFIABLE"
    assert checked["passed"] is False
    assert checked["issues"] == []


def test_neutral_christmas_summary_does_not_rewrite():
    state = initial_state(documents=[], user_prompt="", topic="Christmas")
    state["summary"] = "Some people mention gifts. A few posts describe taking decorations down."
    state["claims"] = [
        {
            "subject": "Some people",
            "predicate": "mention",
            "object": "gifts",
            "scope": "some",
            "claim_type": "observation",
            "text": state["summary"],
            "relevant_entities": [],
        }
    ]
    state["query_results"] = []
    state["query_results_by_claim"] = [{"claim_index": index, "results": []} for index, _ in enumerate(state["claims"])]
    checked = evaluate(state)
    assert checked["passed"] is False
    assert checked["issues"] == []
    assert route_after_evaluate({**state, **checked}) == "end"


def test_live_christmas_facts_match_the_ontology():
    america = run_sparql("america_type", _type(":america"))
    christmas = run_sparql("christmas_type", _type(":christmas"))
    holiday = run_sparql("holiday", _holiday())
    assert "Country" in {row["type"] for row in america["rows"]}
    assert "PublicHolidayEvent" in {row["type"] for row in christmas["rows"]}
    assert {"country": "america", "holiday": "christmas"} in holiday["rows"]


def _type(individual):
    return f"""PREFIX : <http://www.semanticweb.org/ewill/ontologies/2026/8/projectOntology#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?type WHERE {{
  {individual} a ?type .
  FILTER(?type != owl:NamedIndividual && ?type != owl:Thing)
}}"""


def _holiday():
    return """PREFIX : <http://www.semanticweb.org/ewill/ontologies/2026/8/projectOntology#>
SELECT ?country ?holiday WHERE {
  ?country :recognizesPublicHoliday ?holiday .
}"""
