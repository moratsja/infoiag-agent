from src.graph.graph import build_baseline_graph, build_graph


def _names(graph) -> set[str]:
    return set(graph.get_graph().nodes)


def test_agent_graph_contains_the_check_loop():
    names = _names(build_graph())
    assert {
        "summarize",
        "extract_claims",
        "ontology_mapping",
        "select_query",
        "evaluate",
        "rewrite",
    } <= names
    edges = {(edge.source, edge.target) for edge in build_graph().get_graph().edges}
    assert ("summarize", "extract_claims") in edges
    assert ("extract_claims", "ontology_mapping") in edges
    assert ("ontology_mapping", "select_query") in edges
    assert ("select_query", "evaluate") in edges
    assert ("rewrite", "extract_claims") in edges


def test_baseline_graph_is_one_shot():
    names = _names(build_baseline_graph())
    assert "summarize" in names
    assert "extract_claims" not in names
    assert "ontology_mapping" not in names
    assert "select_query" not in names
    assert "evaluate" not in names
    assert "rewrite" not in names
