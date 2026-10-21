from src.graph.graph import initial_state
from src.graph.routing import route_after_evaluate, route_after_extract
from src.nodes.evaluate import evaluate
from src.nodes.extract import extract_summary, format_documents


def _hit(query_id, rows):
    return {
        "query_id": query_id,
        "manchester": "",
        "status": "ok",
        "detail": "test",
        "rows": rows,
    }


def test_extract_splits_summary_sentences():
    state = initial_state(
        documents=[
            {"text": "Lights are up.", "group": "White", "topic": "Christmas"},
            {"text": "I do not celebrate it.", "group": "AA", "topic": "Christmas"},
        ],
        user_prompt="Summarise this.",
        topic="Christmas",
    )
    sentences = extract_summary({**state, "summary": "One view. Another view."})
    assert sentences["summary_sentences"] == ["One view.", "Another view."]


def test_no_claims_stops_before_the_ontology():
    state = initial_state(documents=[], user_prompt="", topic="Christmas")
    assert route_after_extract({**state, "claims": []}) == "end"
    assert route_after_extract({**state, "claims": [{"subject": "America"}]}) == "ontology_mapping"


def test_inconsistent_claim_rewrites_once_then_stops():
    state = initial_state(documents=[], user_prompt="", topic="Christmas", max_revisions=1)
    claim = {
        "subject": "Christmas",
        "predicate": "type",
        "object": "sporting competition",
        "scope": "general",
        "claim_type": "ontology_relation",
        "relevant_entities": ["christmas"],
    }
    state["summary"] = "Christmas is a sporting competition."
    state["claims"] = [claim]
    state["query_results_by_claim"] = [
        {
            "claim_index": 0,
            "template": "individual_type",
            "results": [_hit("individual_type:christmas", [{"type": "PublicHolidayEvent"}])],
        }
    ]
    checked = evaluate(state)
    assert checked["passed"] is False
    assert checked["claim_evaluations"][0]["status"] == "CONTRADICTED"
    assert route_after_evaluate({**state, **checked}) == "rewrite"
    assert route_after_evaluate({**state, **checked, "revision": 1}) == "end"
    assert route_after_evaluate({**state, "passed": True, "revision": 0}) == "end"


def test_not_verifiable_claim_does_not_rewrite():
    state = initial_state(documents=[], user_prompt="", topic="Christmas")
    claim = {
        "subject": "Americans",
        "predicate": "love",
        "object": "Christmas",
        "scope": "general",
        "claim_type": "attitude",
        "text": "Americans love Christmas.",
        "relevant_entities": ["america", "christmas"],
    }
    state["summary"] = claim["text"]
    state["claims"] = [claim]
    state["query_results_by_claim"] = [{"claim_index": 0, "results": []}]
    checked = evaluate(state)
    assert checked["passed"] is True
    assert checked["claim_evaluations"][0]["status"] == "NOT_VERIFIABLE"
    assert checked["issues"] == []
    assert route_after_evaluate({**state, **checked}) == "end"


def test_prompt_keeps_group_off_the_model_input():
    documents = [
        {"text": "Lights are up.", "group": "White", "topic": "Christmas"},
        {"text": "Family dinner.", "group": "Hisp", "topic": "Christmas"},
        {"text": "Not my holiday.", "group": "AA", "topic": "Christmas"},
    ]
    text = format_documents(documents)
    assert "Lights are up." in text
    assert "(White)" not in text
    assert "(Hisp)" not in text
    assert "(AA)" not in text
    assert [doc["group"] for doc in documents] == ["White", "Hisp", "AA"]
