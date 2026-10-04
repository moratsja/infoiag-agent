"""Load the Protégé ontology from ``ontology/ontology.owl``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from src.config import ONTOLOGY_PATH


class OntologyNotFound(FileNotFoundError):
    """Raised when the Protégé export is not at the expected path."""


def ontology_file() -> Path:
    return ONTOLOGY_PATH


def load_ontology():
    """Load and cache the OWL file with owlready2."""
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
    """Return class names from the loaded ontology, for checks in the notebook."""
    onto = load_ontology()
    return sorted(cls.name for cls in onto.classes())
