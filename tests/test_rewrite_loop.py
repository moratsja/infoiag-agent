import importlib
import json

from src.graph.graph import build_graph, initial_state


def _claims(text, obj):
    return json.dumps({
        "claims": [{
            "subject": "Christmas",
            "predicate": "is a",
            "object": obj,
            "scope": "general",
            "claim_type": "factual",
            "relevant_entities": ["christmas"],
            "text": text,
        }]
    })


def _mapping(class_name, text):
    return json.dumps({
        "mappings": [{
            "claim_index": 0,
            "ontology_relevant": True,
            "subject": {"text": "Christmas", "ontology_class": "", "ontology_entity": "christmas"},
            "predicate": {"text": "is a", "ontology_property": ""},
            "object": {"text": text, "ontology_class": class_name, "ontology_entity": ""},
        }]
    })


def _install(monkeypatch, rewrite_text):
    # The RDF file has no individual the checker can contradict.
    # This stub only drives the graph. tests/test_reasoner.py uses the real file.
    def fake_check(mapping):
        class_name = (mapping.get("object") or {}).get("ontology_class")
        if class_name == "SportingCompetitionEvent":
            return {
                "status": "CONTRADICTED",
                "template": "type",
                "message": "Test stub: this verdict is not from the ontology file.",
            }
        if class_name == "Event":
            return {
                "status": "SUPPORTED",
                "template": "type",
                "message": "Test stub: entailed class membership.",
            }
        return {"status": "NOT_VERIFIABLE", "template": None, "message": "Test stub."}

    monkeypatch.setattr(importlib.import_module("src.nodes.select_query"), "check_mapping", fake_check)

    def fake_complete(system, user):
        if system.startswith("Extract claims"):
            if "sporting competition" in user:
                return _claims("Christmas is a sporting competition event.", "sporting competition event")
            return _claims("Christmas is a public holiday event.", "public holiday event")
        if system.startswith("You map"):
            claims = user.split("Claims:", 1)[-1]
            if "sporting competition" in claims.lower():
                return _mapping("SportingCompetitionEvent", "sporting competition event")
            return _mapping("Event", "public holiday event")
        if "Problems to fix" in user:
            return rewrite_text
        return "Christmas is a sporting competition event."

    monkeypatch.setattr("src.llm.model.complete", fake_complete)
    monkeypatch.setattr(importlib.import_module("src.nodes.summarize"), "complete", fake_complete)
    monkeypatch.setattr(importlib.import_module("src.nodes.rewrite"), "complete", fake_complete)


def _state():
    return initial_state(
        documents=[{"text": "Lights are up.", "group": "White", "topic": "Christmas"}],
        user_prompt="Summarise this.",
        topic="Christmas",
        k=1,
        max_revisions=1,
    )


def test_contradicted_claim_is_rewritten_and_checked_again(monkeypatch):
    _install(monkeypatch, "Christmas is a public holiday event.")
    result = build_graph().invoke(_state())
    assert result["trace"].count("rewrite") == 1
    assert result["trace"].count("evaluate") == 2
    assert result["revision"] == 1
    assert result["claim_evaluations"][0]["status"] == "SUPPORTED"
    assert result["issues"] == []
    assert result["passed"] is True


def test_contradiction_remains_after_the_revision_limit(monkeypatch):
    _install(monkeypatch, "Christmas is a sporting competition event.")
    result = build_graph().invoke(_state())
    assert result["trace"].count("rewrite") == 1
    assert result["revision"] == 1
    assert result["claim_evaluations"][0]["status"] == "CONTRADICTED"
    assert result["issues"]
    assert result["passed"] is False
