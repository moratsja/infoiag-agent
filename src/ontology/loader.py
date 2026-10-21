from owlready2 import get_ontology

from src.config import ONTOLOGY_PATH

def load_ontology():
    return get_ontology(str(ONTOLOGY_PATH)).load()