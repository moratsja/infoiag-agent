from src.graph.graph import initial_state
from src.graph.routing import route_after_evaluate
from src.nodes.evaluate import evaluate, find_issues, mean_jaccard_by_group
from src.nodes.extract import extract_summary


def _hit(query_id: str, rows: list[dict[str, str]]) -> dict:
    return {
        "query_id": query_id,
        "manchester": "",
        "status": "ok",
        "detail": "test",
        "rows": rows,
    }


def test_extract_splits_summary_sentences():
    state = initial_state(
        documents=[
            {"text": "Lights are up.", "group": "White", "topic": "Christmas"},
            {"text": "I do not celebrate it.", "group": "AA", "topic": "Christmas"},
        ],
        user_prompt="Summarise this.",
        topic="Christmas",
    )
    sentences = extract_summary({**state, "summary": "One view. Another view."})
    assert sentences["summary_sentences"] == ["One view.", "Another view."]


def test_holiday_recognition_blocks_a_universal_christmas_claim():
    issues = find_issues(
        "Americans love to celebrate Christmas.",
        [_hit("q5_america_recognizes_christmas", [{"country": "america", "holiday": "christmas"}])],
    )
    assert issues[0]["kind"] == "bias"
    assert "america" in issues[0]["message"]
    assert "christmas" in issues[0]["message"]


def test_universal_christmas_claim_needs_a_query_hit():
    summary = "All Americans love to celebrate Christmas."
    issues = find_issues(
        summary,
        [_hit("q1_americans_not_celebrating_christmas", [{"person": "ada"}])],
    )
    assert issues[0]["kind"] == "bias"
    assert "ada" in issues[0]["message"]


def test_hedged_christmas_claim_passes():
    issues = find_issues(
        "Not all Americans celebrate Christmas.",
        [_hit("q1_americans_not_celebrating_christmas", [{"person": "ada"}])],
    )
    assert issues == []


def test_query_error_does_not_become_an_issue():
    result = _hit("q1_americans_not_celebrating_christmas", [])
    result["status"] = "error"
    issues = find_issues("All Americans love Christmas.", [result])
    assert issues == []


def test_empty_query_is_not_treated_as_a_contradiction():
    issues = find_issues(
        "All Americans love Christmas.",
        [_hit("q1_americans_not_celebrating_christmas", [])],
    )
    assert issues == []


def test_route_rewrites_once_then_stops():
    state = initial_state(documents=[], user_prompt="", topic="Christmas", max_revisions=1)
    failed = evaluate({**state, "summary": "", "query_results": []})
    assert failed["passed"] is False
    assert route_after_evaluate({**state, **failed}) == "rewrite"
    state["revision"] = 1
    assert route_after_evaluate({**state, **failed}) == "end"
    assert route_after_evaluate({**state, "passed": True, "revision": 0}) == "end"


def test_jaccard_is_higher_for_the_overlapping_group():
    documents = [
        {"text": "posadas family december", "group": "Hisp", "topic": "Christmas"},
        {"text": "unrelated basketball score", "group": "White", "topic": "Christmas"},
    ]
    scores = mean_jaccard_by_group("posadas with family in december", documents)
    assert scores["Hisp"] > scores["White"]
