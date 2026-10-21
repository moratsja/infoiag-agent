# Owlready2's sync_reasoner runs HermiT, so java has to be installed.

import shutil
from pathlib import Path

import owlready2
from owlready2 import Not, OwlReadyInconsistentOntologyError, World, sync_reasoner

from src.config import ONTOLOGY_PATH

_BEFORE = "The ontology is inconsistent before the claim is added, so the claim is not classified."

def _java_command():
    found = shutil.which("java")
    if found:
        return found
    root = Path(r"C:\Program Files\Eclipse Adoptium")
    matches = sorted(root.glob("*/bin/java.exe")) if root.is_dir() else []
    if matches:
        return str(matches[-1])
    return "java"

owlready2.JAVA_EXE = _java_command()

def claim_shape(mapping):
    if not mapping:
        return None
    subject = (mapping.get("subject") or {}).get("ontology_entity") or ""
    prop = (mapping.get("predicate") or {}).get("ontology_property") or ""
    obj = mapping.get("object") or {}
    object_entity = obj.get("ontology_entity") or ""
    object_class = obj.get("ontology_class") or ""
    if subject and prop and object_entity:
        return "relation"
    if subject and object_class and not prop and not object_entity:
        return "type"
    return None

def check_mapping(mapping):
    shape = claim_shape(mapping)
    if shape is None:
        return _result(
            "NOT_VERIFIABLE",
            None,
            "This claim is not a class membership or an object property between individuals. It is not verifiable.",
        )
    try:
        if shape == "type":
            return _check_type(mapping["subject"]["ontology_entity"], mapping["object"]["ontology_class"])
        return _check_relation(
            mapping["subject"]["ontology_entity"],
            mapping["predicate"]["ontology_property"],
            mapping["object"]["ontology_entity"],
        )
    except Exception as exc:
        return _result("NOT_VERIFIABLE", shape, f"Reasoner error: {type(exc).__name__}: {exc}")

def _check_type(individual_name, class_name):
    world, onto = _load_world()
    if getattr(onto, individual_name, None) is None:
        return _result("NOT_VERIFIABLE", "type", f"Unknown individual '{individual_name}'. The claim is not verifiable.")
    if getattr(onto, class_name, None) is None:
        return _result("NOT_VERIFIABLE", "type", f"Unknown class '{class_name}'. The claim is not verifiable.")
    ok, problem = _run(world)
    if problem or not ok:
        return _result("NOT_VERIFIABLE", "type", problem or _BEFORE)
    world, onto = _load_world()
    with onto:
        getattr(onto, individual_name).is_a.append(Not(getattr(onto, class_name)))
    entailed, problem = _inconsistent(world)
    if problem:
        return _result("NOT_VERIFIABLE", "type", problem)
    if entailed:
        return _result("SUPPORTED", "type", f"The reasoner finds that {individual_name} type {class_name} follows.")
    world, onto = _load_world()
    with onto:
        getattr(onto, individual_name).is_a.append(getattr(onto, class_name))
    contradicted, problem = _inconsistent(world)
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

def _check_relation(subject_name, prop_name, object_name):
    world, onto = _load_world()
    if getattr(onto, subject_name, None) is None or getattr(onto, object_name, None) is None:
        missing = subject_name if getattr(onto, subject_name, None) is None else object_name
        return _result("NOT_VERIFIABLE", "relation", f"Unknown individual '{missing}'. The claim is not verifiable.")
    prop = getattr(onto, prop_name, None)
    if prop is None or not isinstance(prop, owlready2.ObjectPropertyClass):
        return _result("NOT_VERIFIABLE", "relation", f"Unknown object property '{prop_name}'. The claim is not verifiable.")
    ok, problem = _run(world)
    if problem or not ok:
        return _result("NOT_VERIFIABLE", "relation", problem or _BEFORE)
    if getattr(onto, object_name) in list(getattr(getattr(onto, subject_name), prop_name)):
        return _result("SUPPORTED", "relation", f"The reasoner finds that {subject_name} {prop_name} {object_name} holds.")
    world, onto = _load_world()
    with onto:
        getattr(getattr(onto, subject_name), prop_name).append(getattr(onto, object_name))
    contradicted, problem = _inconsistent(world)
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

def _load_world():
    world = World()
    onto = world.get_ontology(str(ONTOLOGY_PATH)).load()
    return world, onto

def _run(world):
    try:
        sync_reasoner(world, infer_property_values=True, debug=0)
    except OwlReadyInconsistentOntologyError:
        return False, None
    except Exception as exc:
        return False, f"Reasoner error: {type(exc).__name__}: {exc}"
    return True, None

def _inconsistent(world):
    consistent, problem = _run(world)
    if problem:
        return False, problem
    return (not consistent), None

def _result(status, template, message):
    return {"status": status, "template": template, "message": message}
