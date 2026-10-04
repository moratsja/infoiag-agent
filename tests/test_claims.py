from src.config import MAX_REVISIONS
from src.graph.graph import initial_state
from src.graph.routing import route_after_evaluate
from src.nodes.claims import fallback_claims, parse_claims
from src.nodes.evaluate import evaluate, judge_claim
from src.ontology.claim_queries import queries_for_claim
from src.ontology.loader import _load
from src.ontology.tools import run_sparql


def test_parse_claims_accepts_structured_json():
    payload = """
    {"claims": [{
      "subject": "Americans",
      "predicate": "love",
      "object": "Christmas",
      "scope": "all",
      "claim_type": "attitude",
      "confidence": 0.95,
      "relevant_entities": ["America", "christmas"]
    }]}
    """
    claim = parse_claims(payload)[0].model_dump(by_alias=True)
    assert claim["scope"] == "universal"
    assert claim["object"] == "Christmas"
    assert claim["claim_type"] == "attitude"


def test_fallback_marks_all_americans_as_universal():
    claim = fallback_claims("All Americans love Christmas.")[0].model_dump(by_alias=True)
    assert claim["scope"] == "universal"
    assert claim["predicate"] == "love"


def test_supported_holiday_claim():
    claim = {
        "subject": "America",
        "predicate": "recognizesPublicHoliday",
        "object": "Christmas",
        "scope": "general",
        "claim_type": "ontology_relation",
        "relevant_entities": ["america", "christmas"],
    }
    verdict = judge_claim(claim, [_ok("recognizes_public_holiday", [{"country": "america", "holiday": "christmas"}])])
    assert verdict["status"] == "SUPPORTED"


def test_contradicted_type_claim():
    claim = {
        "subject": "Christmas",
        "predicate": "type",
        "object": "sporting competition",
        "scope": "general",
        "claim_type": "ontology_relation",
        "relevant_entities": ["christmas"],
    }
    verdict = judge_claim(claim, [_ok("individual_type:christmas", [{"type": "PublicHolidayEvent"}])])
    assert verdict["status"] == "CONTRADICTED"


def test_love_claim_is_not_verifiable_from_the_holiday_fact():
    claim = fallback_claims("Americans love Christmas.")[0].model_dump(by_alias=True)
    verdict = judge_claim(claim, [])
    assert verdict["status"] == "NOT_VERIFIABLE"


def test_broad_christmas_claim_is_rewritten_and_checked_again():
    state = initial_state(documents=[], user_prompt="why Americans love Christmas", topic="Christmas", max_revisions=1)
    state["summary"] = "Americans love Christmas."
    state["claims"] = [fallback_claims(state["summary"])[0].model_dump(by_alias=True)]
    state["query_results"] = []
    state["query_results_by_claim"] = [{"claim_index": 0, "results": []}]
    checked = evaluate(state)
    assert checked["passed"] is False
    assert route_after_evaluate({**state, **checked}) == "rewrite"
    state["revision"] = 1
    state["summary"] = "Some posts mention gifts. Others mention decorations left up."
    state["claims"] = [item.model_dump(by_alias=True) for item in fallback_claims(state["summary"])]
    state["query_results_by_claim"] = [{"claim_index": index, "results": []} for index, _ in enumerate(state["claims"])]
    checked_again = evaluate(state)
    assert checked_again["passed"] is True
    assert route_after_evaluate({**state, **checked_again}) == "end"
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
    assert evaluate(state)["passed"] is True


def test_group_specific_enthusiasm_is_not_a_broad_claim():
    claim = {
        "subject": "White and Hispanic individuals",
        "predicate": "show enthusiasm for celebrating",
        "object": "Christmas",
        "scope": "general",
        "claim_type": "attitude",
        "relevant_entities": ["christmas"],
    }
    verdict = judge_claim(claim, [])
    state = initial_state(documents=[], user_prompt="", topic="Christmas")
    state["summary"] = "Some White and Hispanic posts describe gifts."
    state["claims"] = [claim]
    state["query_results"] = []
    state["query_results_by_claim"] = [{"claim_index": 0, "results": []}]
    checked = evaluate(state)
    assert verdict["status"] == "NOT_VERIFIABLE"
    assert checked["passed"] is True


def test_neutral_christmas_summary_does_not_rewrite():
    state = initial_state(documents=[], user_prompt="", topic="Christmas")
    state["summary"] = "Some people mention gifts. A few posts describe taking decorations down."
    state["claims"] = [item.model_dump(by_alias=True) for item in fallback_claims(state["summary"])]
    state["query_results"] = []
    state["query_results_by_claim"] = [{"claim_index": index, "results": []} for index, _ in enumerate(state["claims"])]
    checked = evaluate(state)
    assert checked["passed"] is True
    assert route_after_evaluate({**state, **checked}) == "end"


def test_live_christmas_facts_match_the_ontology():
    _load.cache_clear()
    try:
        america = run_sparql("america_type", _type(":america"))
        christmas = run_sparql("christmas_type", _type(":christmas"))
        holiday = run_sparql("holiday", _holiday())
        mapped = queries_for_claim(
            {
                "subject": "America",
                "predicate": "recognizesPublicHoliday",
                "object": "Christmas",
                "relevant_entities": ["america", "christmas"],
            }
        )
    finally:
        _load.cache_clear()
    assert "Country" in {row["type"] for row in america["rows"]}
    assert "PublicHolidayEvent" in {row["type"] for row in christmas["rows"]}
    assert {"country": "america", "holiday": "christmas"} in holiday["rows"]
    assert mapped[0]["status"] == "ok"
    assert {"country": "america", "holiday": "christmas"} in mapped[0]["rows"]


def _ok(query_id: str, rows: list[dict]) -> dict:
    return {"query_id": query_id, "manchester": "", "status": "ok", "detail": "test", "rows": rows}


def _type(individual: str) -> str:
    return f"""PREFIX : <http://www.semanticweb.org/ewill/ontologies/2026/8/projectOntology#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?type WHERE {{
  {individual} a ?type .
  FILTER(?type != owl:NamedIndividual && ?type != owl:Thing)
}}"""


def _holiday() -> str:
    return """PREFIX : <http://www.semanticweb.org/ewill/ontologies/2026/8/projectOntology#>
SELECT ?country ?holiday WHERE {
  ?country :recognizesPublicHoliday ?holiday .
}"""
