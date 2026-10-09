# Load ontologyStefan.rdf once and reuse it.

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from src.config import ONTOLOGY_PATH


class OntologyNotFound(FileNotFoundError):
    pass


def ontology_file() -> Path:
    return ONTOLOGY_PATH


def load_ontology():
    return _load(str(ontology_file()))


@lru_cache(maxsize=4)
def _load(path_str: str):
    path = Path(path_str)
    if not path.is_file():
        raise OntologyNotFound(
            f"Ontology file not found: {path}. Export the Protégé ontology to this path."
        )
    from owlready2 import get_ontology

    return get_ontology(path.as_uri()).load()


def list_class_names() -> list[str]:
    onto = load_ontology()
    return sorted(cls.name for cls in onto.classes())
