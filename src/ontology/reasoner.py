# Check one mapped claim with HermiT on a temporary copy of the ontology.
# The RDF file is not changed. Two claim shapes are supported:
# an individual belonging to a class, or an object property between two individuals.

import shutil
from pathlib import Path

import owlready2
from owlready2 import AllDisjoint, Not, OwlReadyInconsistentOntologyError, World, sync_reasoner_hermit

from src.config import ONTOLOGY_PATH

# Not in ontologyStefan.rdf. Added only in memory so the sporting-competition
# proof of concept has a real contradiction to test. Both classes are subclasses of Event.
POC_DISJOINT = ("PublicHolidayEvent", "SportingCompetitionEvent")


def _configure_java():
    found = shutil.which("java")
    if found:
        owlready2.JAVA_EXE = found
        return
    root = Path(r"C:\Program Files\Eclipse Adoptium")
    matches = sorted(root.glob("*/bin/java.exe")) if root.is_dir() else []
    if matches:
        owlready2.JAVA_EXE = str(matches[-1])


_configure_java()


def claim_shape(mapping):
    # A usable mapping is exactly one of the two shapes. Anything mixed or empty is skipped.
    if not mapping:
        return None
    subject = mapping.get("subject") or {}
    predicate = mapping.get("predicate") or {}
    obj = mapping.get("object") or {}
    subject_entity = subject.get("ontology_entity") or ""
    prop = predicate.get("ontology_property") or ""
    object_entity = obj.get("ontology_entity") or ""
    object_class = obj.get("ontology_class") or ""
    # A class name next to an individual is only a label. The check uses the individuals and the property.
    if subject_entity and prop and object_entity:
        return "relation"
    if subject_entity and object_class and not prop and not object_entity:
        return "type"
    return None


def check_mapping(mapping, use_poc_disjoint = True):
    shape = claim_shape(mapping)
    if shape is None:
        return _result(
            "NOT_VERIFIABLE",
            None,
            "This claim is not a class membership or an object property between individuals. It is not verifiable.",
        )
    try:
        if shape == "type":
            return _check_type(mapping, use_poc_disjoint)
        return _check_relation(mapping, use_poc_disjoint)
    except Exception as exc:
        return _result("NOT_VERIFIABLE", shape, f"Reasoner error: {type(exc).__name__}: {exc}")


def _check_type(mapping, use_poc_disjoint):
    individual_name = mapping["subject"]["ontology_entity"]
    class_name = mapping["object"]["ontology_class"]
    world, onto = _load_world(use_poc_disjoint)
    missing = _missing_type_names(onto, individual_name, class_name)
    if missing:
        return _result("NOT_VERIFIABLE", "type", missing)
    base_ok, problem = _run(world)
    if problem:
        return _result("NOT_VERIFIABLE", "type", problem)
    if not base_ok:
        return _result(
            "NOT_VERIFIABLE",
            "type",
            "The ontology is inconsistent before the claim is added, so the claim is not classified.",
        )
    entailed, problem = _type_is_entailed(individual_name, class_name, use_poc_disjoint)
    if problem:
        return _result("NOT_VERIFIABLE", "type", problem)
    if entailed:
        return _result(
            "SUPPORTED",
            "type",
            f"HermiT finds that the ontology entails {individual_name} type {class_name}.",
        )
    contradicted, problem = _adding_type_is_inconsistent(individual_name, class_name, use_poc_disjoint)
    if problem:
        return _result("NOT_VERIFIABLE", "type", problem)
    if contradicted:
        return _result(
            "CONTRADICTED",
            "type",
            f"Adding {individual_name} type {class_name} makes a consistent ontology inconsistent.",
        )
    return _result(
        "NOT_VERIFIABLE",
        "type",
        f"The ontology does not entail {individual_name} type {class_name}, and adding it stays consistent.",
    )


def _check_relation(mapping, use_poc_disjoint):
    subject_name = mapping["subject"]["ontology_entity"]
    prop_name = mapping["predicate"]["ontology_property"]
    object_name = mapping["object"]["ontology_entity"]
    world, onto = _load_world(use_poc_disjoint)
    missing = _missing_relation_names(onto, subject_name, prop_name, object_name)
    if missing:
        return _result("NOT_VERIFIABLE", "relation", missing)
    consistent, problem = _run(world)
    if problem:
        return _result("NOT_VERIFIABLE", "relation", problem)
    if not consistent:
        return _result(
            "NOT_VERIFIABLE",
            "relation",
            "The ontology is inconsistent before the claim is added, so the claim is not classified.",
        )
    if _has_relation(onto, subject_name, prop_name, object_name):
        return _result(
            "SUPPORTED",
            "relation",
            f"HermiT finds that {subject_name} {prop_name} {object_name} holds.",
        )
    contradicted, problem = _adding_relation_is_inconsistent(
        subject_name, prop_name, object_name, use_poc_disjoint
    )
    if problem:
        return _result("NOT_VERIFIABLE", "relation", problem)
    if contradicted:
        return _result(
            "CONTRADICTED",
            "relation",
            f"Adding {subject_name} {prop_name} {object_name} makes a consistent ontology inconsistent.",
        )
    return _result(
        "NOT_VERIFIABLE",
        "relation",
        f"The ontology does not entail {subject_name} {prop_name} {object_name}. A different pair is not used as evidence.",
    )


def _type_is_entailed(individual_name, class_name, use_poc_disjoint):
    # O entails the type when O plus the negation is inconsistent.
    world, onto = _load_world(use_poc_disjoint)
    missing = _missing_type_names(onto, individual_name, class_name)
    if missing:
        return False, missing
    _add_type(onto, individual_name, class_name, negated = True)
    consistent, problem = _run(world)
    if problem:
        return False, problem
    return (not consistent), None


def _adding_type_is_inconsistent(individual_name, class_name, use_poc_disjoint):
    world, onto = _load_world(use_poc_disjoint)
    missing = _missing_type_names(onto, individual_name, class_name)
    if missing:
        return False, missing
    _add_type(onto, individual_name, class_name, negated = False)
    consistent, problem = _run(world)
    if problem:
        return False, problem
    return (not consistent), None


def _adding_relation_is_inconsistent(subject_name, prop_name, object_name, use_poc_disjoint):
    world, onto = _load_world(use_poc_disjoint)
    missing = _missing_relation_names(onto, subject_name, prop_name, object_name)
    if missing:
        return False, missing
    with onto:
        getattr(getattr(onto, subject_name), prop_name).append(getattr(onto, object_name))
    consistent, problem = _run(world)
    if problem:
        return False, problem
    return (not consistent), None


def _load_world(use_poc_disjoint):
    world = World()
    onto = world.get_ontology(str(ONTOLOGY_PATH)).load()
    if use_poc_disjoint:
        with onto:
            AllDisjoint([onto.PublicHolidayEvent, onto.SportingCompetitionEvent])
    return world, onto


def _run(world):
    try:
        sync_reasoner_hermit(world, infer_property_values = True, debug = 0)
    except OwlReadyInconsistentOntologyError:
        return False, None
    except Exception as exc:
        return False, f"Reasoner error: {type(exc).__name__}: {exc}"
    return True, None


def _add_type(onto, individual_name, class_name, negated):
    individual = getattr(onto, individual_name)
    cls = getattr(onto, class_name)
    with onto:
        if negated:
            individual.is_a.append(Not(cls))
        else:
            individual.is_a.append(cls)


def _missing_type_names(onto, individual_name, class_name):
    if getattr(onto, individual_name, None) is None:
        return f"Unknown individual '{individual_name}'. The claim is not verifiable."
    if getattr(onto, class_name, None) is None:
        return f"Unknown class '{class_name}'. The claim is not verifiable."
    return None


def _missing_relation_names(onto, subject_name, prop_name, object_name):
    if getattr(onto, subject_name, None) is None:
        return f"Unknown individual '{subject_name}'. The claim is not verifiable."
    if getattr(onto, object_name, None) is None:
        return f"Unknown individual '{object_name}'. The claim is not verifiable."
    prop = getattr(onto, prop_name, None)
    if prop is None or not isinstance(prop, owlready2.ObjectPropertyClass):
        return f"Unknown object property '{prop_name}'. The claim is not verifiable."
    return None


def _has_relation(onto, subject_name, prop_name, object_name):
    subject = getattr(onto, subject_name)
    obj = getattr(onto, object_name)
    return obj in list(getattr(subject, prop_name))


def _result(status, template, message):
    return {"status": status, "template": template, "message": message}
