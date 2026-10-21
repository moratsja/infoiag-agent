from owlready2 import World

from src.config import ONTOLOGY_PATH
from src.ontology import reasoner
from src.ontology.reasoner import check_mapping


def _type_mapping(individual, class_name):
    return {
        "subject": {"text": individual, "ontology_class": "", "ontology_entity": individual},
        "predicate": {"text": "is a", "ontology_property": ""},
        "object": {"text": class_name, "ontology_class": class_name, "ontology_entity": ""},
    }


def _relation_mapping(subject, prop, obj):
    return {
        "subject": {"text": subject, "ontology_class": "", "ontology_entity": subject},
        "predicate": {"text": prop, "ontology_property": prop},
        "object": {"text": obj, "ontology_class": "", "ontology_entity": obj},
    }


def test_asserted_type_is_not_already_the_superclass():
    world = World()
    onto = world.get_ontology(str(ONTOLOGY_PATH)).load()
    direct = [cls.name for cls in onto.christmas.is_a if getattr(cls, "name", None)]
    assert direct == ["PublicHolidayEvent"]
    assert "Event" not in direct


def test_reasoner_infers_event_superclass():
    verdict = check_mapping(_type_mapping("christmas", "Event"))
    assert verdict["status"] == "SUPPORTED"
    assert "Event" in verdict["message"]


def test_public_holiday_type_is_supported():
    verdict = check_mapping(_type_mapping("christmas", "PublicHolidayEvent"))
    assert verdict["status"] == "SUPPORTED"


def test_sporting_type_is_contradicted_with_the_poc_disjointness():
    verdict = check_mapping(_type_mapping("christmas", "SportingCompetitionEvent"))
    assert verdict["status"] == "CONTRADICTED"


def test_sporting_type_is_not_verifiable_without_the_poc_disjointness():
    verdict = check_mapping(_type_mapping("christmas", "SportingCompetitionEvent"), use_poc_disjoint = False)
    assert verdict["status"] == "NOT_VERIFIABLE"


def test_a_different_class_is_not_a_contradiction_by_itself():
    verdict = check_mapping(_type_mapping("christmas", "Country"))
    assert verdict["status"] == "NOT_VERIFIABLE"


def test_americans_love_christmas_is_not_verifiable():
    verdict = check_mapping({
        "subject": {"text": "Americans", "ontology_class": "", "ontology_entity": ""},
        "predicate": {"text": "love", "ontology_property": ""},
        "object": {"text": "Christmas", "ontology_class": "", "ontology_entity": "christmas"},
    })
    assert verdict["status"] == "NOT_VERIFIABLE"


def test_america_recognizes_christmas():
    verdict = check_mapping(_relation_mapping("america", "recognizesPublicHoliday", "christmas"))
    assert verdict["status"] == "SUPPORTED"


def test_another_pair_is_not_supported_from_the_america_row():
    verdict = check_mapping(_relation_mapping("evaPerson", "recognizesPublicHoliday", "christmas"))
    assert verdict["status"] == "NOT_VERIFIABLE"


def test_unknown_individual_is_not_verifiable():
    verdict = check_mapping(_type_mapping("atlantis", "Event"))
    assert verdict["status"] == "NOT_VERIFIABLE"
    assert "Unknown individual" in verdict["message"]


def test_unknown_property_is_not_verifiable():
    verdict = check_mapping(_relation_mapping("america", "loves", "christmas"))
    assert verdict["status"] == "NOT_VERIFIABLE"
    assert "Unknown object property" in verdict["message"]


def test_inconsistent_ontology_is_not_called_a_contradiction(monkeypatch):
    def inconsistent(world):
        return False, None

    monkeypatch.setattr(reasoner, "_run", inconsistent)
    verdict = check_mapping(_type_mapping("christmas", "Event"))
    assert verdict["status"] == "NOT_VERIFIABLE"
    assert "inconsistent before" in verdict["message"]


def test_reasoner_failure_is_not_called_a_contradiction(monkeypatch):
    def broken(world):
        return False, "Reasoner error: RuntimeError: java missing"

    monkeypatch.setattr(reasoner, "_run", broken)
    verdict = check_mapping(_type_mapping("christmas", "Event"))
    assert verdict["status"] == "NOT_VERIFIABLE"
    assert verdict["message"].startswith("Reasoner error")
