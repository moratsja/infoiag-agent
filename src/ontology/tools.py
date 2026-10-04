"""Tools used by the ontology tool nodes.

``run_queries_for_text`` is the tool both ontology nodes call.
``list_classes`` is available for inspection and is not part of the rewrite decision.
"""

from __future__ import annotations

import re

from src.graph.state import QueryResult
from src.ontology.loader import OntologyNotFound, list_class_names, load_ontology
from src.ontology.queries import OntologyQuery, select_queries


def list_classes() -> list[str]:
    return list_class_names()


def run_queries_for_text(topic: str, text: str) -> list[QueryResult]:
    """Select Intermediate Report 1 queries and execute each one."""
    return [run_query(query) for query in select_queries(topic, text)]


def run_sparql(query_id: str, sparql: str, manchester: str = "") -> QueryResult:
    """Run one fixed SPARQL string. Used by claim templates and by registered queries."""
    try:
        onto = load_ontology()
        rows = _run_sparql(onto, sparql)
    except OntologyNotFound as exc:
        return _error_parts(query_id, manchester, str(exc))
    except Exception as exc:
        return _error_parts(query_id, manchester, f"{type(exc).__name__}: {exc}")
    return {
        "query_id": query_id,
        "manchester": manchester,
        "status": "ok",
        "detail": "sparql-closed-world",
        "rows": rows,
    }


def run_query(query: OntologyQuery) -> QueryResult:
    """Execute one registered query. A missing ontology is reported on the result, not raised."""
    result = run_sparql(query.id, query.sparql, query.manchester)
    return result


def _error_parts(query_id: str, manchester: str, detail: str) -> QueryResult:
    return {
        "query_id": query_id,
        "manchester": manchester,
        "status": "error",
        "detail": detail,
        "rows": [],
    }


def _run_sparql(onto, sparql: str) -> list[dict[str, str]]:
    variables = _select_variables(sparql)
    rows: list[dict[str, str]] = []
    for binding in onto.world.sparql(sparql, error_on_undefined_entities=False):
        values = binding if isinstance(binding, (list, tuple)) else [binding]
        labels = [_label(value) for value in values]
        if len(variables) == len(labels):
            rows.append(dict(zip(variables, labels)))
        else:
            rows.append({f"col_{index}": label for index, label in enumerate(labels)})
    return rows


def _select_variables(sparql: str) -> list[str]:
    match = re.search(r"SELECT\s+(.*?)\s+WHERE", sparql, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    return [name[1:] for name in re.findall(r"\?\w+", match.group(1))]


def _label(value) -> str:
    if value is None:
        return ""
    name = getattr(value, "name", None)
    if name:
        return str(name)
    return str(value)
