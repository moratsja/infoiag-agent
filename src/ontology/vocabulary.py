# Compact view of the RDF file for the mapper. Not the raw XML.

from functools import lru_cache

from rdflib import OWL, RDF, RDFS, Graph, URIRef
from rdflib.collection import Collection

from src.ontology.loader import ontology_file

_SKIP = {"Thing", "Nothing", "Class", "NamedIndividual", "ObjectProperty", "DatatypeProperty"}


def local_name(uri) -> str:
    text = str(uri)
    if "#" in text:
        return text.split("#")[-1]
    return text.rstrip("/").split("/")[-1]


def load_vocabulary(path=None):
    # Classes, object properties, and individuals. Datatype properties are left out.
    target = str(path or ontology_file())
    return _load(target)


@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    graph = Graph()
    graph.parse(path, format="xml")
    return {
        "classes": _classes(graph),
        "object_properties": _properties(graph),
        "individuals": _individuals(graph),
    }


def _classes(graph: Graph) -> list[dict]:
    rows = []
    for cls in graph.subjects(RDF.type, OWL.Class):
        if not isinstance(cls, URIRef):
            continue
        name = local_name(cls)
        if name in _SKIP:
            continue
        parents = []
        for parent in graph.objects(cls, RDFS.subClassOf):
            if not isinstance(parent, URIRef):
                continue
            parent_name = local_name(parent)
            if parent_name not in _SKIP:
                parents.append(parent_name)
        rows.append({"name": name, "subclass_of": sorted(set(parents))})
    return sorted(rows, key=lambda row: row["name"])


def _properties(graph: Graph) -> list[dict]:
    rows = []
    for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
        if not isinstance(prop, URIRef):
            continue
        rows.append(
            {
                "name": local_name(prop),
                "domain": _class_names(graph, list(graph.objects(prop, RDFS.domain))),
                "range": _class_names(graph, list(graph.objects(prop, RDFS.range))),
            }
        )
    return sorted(rows, key=lambda row: row["name"])


def _individuals(graph: Graph) -> list[dict]:
    rows = []
    for individual in graph.subjects(RDF.type, OWL.NamedIndividual):
        if not isinstance(individual, URIRef):
            continue
        classes = []
        for cls in graph.objects(individual, RDF.type):
            if isinstance(cls, URIRef) and local_name(cls) not in _SKIP:
                classes.append(local_name(cls))
        rows.append({"name": local_name(individual), "classes": sorted(set(classes))})
    return sorted(rows, key=lambda row: row["name"])


def _class_names(graph: Graph, nodes: list) -> list[str]:
    names = []
    for node in nodes:
        names.extend(_names_from_node(graph, node))
    return sorted({name for name in names if name and name not in _SKIP})


def _names_from_node(graph: Graph, node) -> list[str]:
    if isinstance(node, URIRef):
        return [local_name(node)]
    names = []
    for union in graph.objects(node, OWL.unionOf):
        for item in Collection(graph, union):
            names.extend(_names_from_node(graph, item))
    return names
