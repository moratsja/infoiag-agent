from src.nodes.ontology_mapping import parse_mappings
from src.nodes.select_query import select_query
from src.ontology.vocabulary import load_vocabulary


def test_vocabulary_has_the_christmas_facts():
    vocabulary = load_vocabulary()
    classes = {row["name"] for row in vocabulary["classes"]}
    properties = {row["name"]: row for row in vocabulary["object_properties"]}
    individuals = {row["name"]: row for row in vocabulary["individuals"]}
    assert "Country" in classes
    assert "PublicHolidayEvent" in classes
    holiday = properties["recognizesPublicHoliday"]
    assert holiday["domain"] == ["Country"]
    assert holiday["range"] == ["PublicHolidayEvent"]
    assert "Country" in individuals["america"]["classes"]
    assert "PublicHolidayEvent" in individuals["christmas"]["classes"]


def test_parse_mappings_drops_invented_names():
    vocabulary = {
        "classes": [{"name": "Country"}, {"name": "PublicHolidayEvent"}],
        "object_properties": [{"name": "recognizesPublicHoliday"}],
        "individuals": [{"name": "america"}, {"name": "christmas"}],
    }
    payload = """
    {"mappings": [{
      "ontology_relevant": true,
      "subject": {"text": "Americans", "ontology_class": "Person", "ontology_entity": "america"},
      "predicate": {"text": "celebrate", "ontology_property": "madeUpProperty"},
      "object": {"text": "Christmas", "ontology_class": "PublicHolidayEvent", "ontology_entity": "christmas"}
    }]}
    """
    mapping = parse_mappings(payload, 1, vocabulary)[0]
    assert mapping["predicate"]["ontology_property"] == ""
    assert mapping["subject"]["ontology_class"] == ""
    assert mapping["subject"]["ontology_entity"] == "america"
    assert mapping["claim_index"] == 0
    assert mapping["ontology_relevant"] is False


def test_type_mapping_is_kept_when_the_class_is_known():
    vocabulary = load_vocabulary()
    payload = """
    {"mappings": [{
      "claim_index": 0,
      "ontology_relevant": true,
      "subject": {"text": "Christmas", "ontology_class": "", "ontology_entity": "christmas"},
      "predicate": {"text": "is a", "ontology_property": ""},
      "object": {"text": "a public holiday", "ontology_class": "PublicHolidayEvent", "ontology_entity": ""}
    }]}
    """
    mapping = parse_mappings(payload, 1, vocabulary)[0]
    assert mapping["ontology_relevant"] is True
    assert mapping["object"]["ontology_class"] == "PublicHolidayEvent"


def test_select_query_checks_the_mapped_holiday_pair():
    state = {
        "claims": [{"subject": "America", "predicate": "recognizes", "object": "Christmas"}],
        "mapped_claims": [
            {
                "claim_index": 0,
                "ontology_relevant": True,
                "subject": {"text": "America", "ontology_class": "Country", "ontology_entity": "america"},
                "predicate": {"text": "recognizes", "ontology_property": "recognizesPublicHoliday"},
                "object": {"text": "Christmas", "ontology_class": "PublicHolidayEvent", "ontology_entity": "christmas"},
            }
        ],
    }
    result = select_query(state)
    checked = result["query_results_by_claim"][0]
    assert checked["claim_index"] == 0
    assert checked["template"] == "relation"
    assert checked["status"] == "SUPPORTED"


def test_unknown_property_does_not_run_a_query():
    state = {
        "claims": [{"subject": "Americans", "predicate": "love", "object": "Christmas"}],
        "mapped_claims": [
            {
                "ontology_relevant": True,
                "subject": {"text": "Americans", "ontology_class": "", "ontology_entity": ""},
                "predicate": {"text": "love", "ontology_property": ""},
                "object": {"text": "Christmas", "ontology_class": "", "ontology_entity": "christmas"},
            }
        ],
    }
    result = select_query(state)
    checked = result["query_results_by_claim"][0]
    assert checked["template"] is None
    assert checked["status"] == "NOT_VERIFIABLE"
