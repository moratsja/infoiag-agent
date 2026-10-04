from pathlib import Path

from src.config import DATA_RAW, ONTOLOGY_IRI, USER_PROMPTS, load_documents, load_reference_summaries
from src.ontology.loader import list_class_names
from src.ontology.loader import _load
from src.ontology import loader
from src.ontology.queries import QUERIES, get_query, select_queries
from src.ontology.tools import run_query


def test_report_queries_are_registered():
    ids = [query.id for query in QUERIES]
    assert ids == [
        "q1_americans_not_celebrating_christmas",
        "q2_positive_netflix_reviews",
        "q3_netflix_cities",
        "q4_netflix_offered_content",
        "q5_america_recognizes_christmas",
    ]
    assert "not (isParticipantOf value christmas)" in get_query(ids[0]).manchester
    assert "hasPositiveContent value true" in get_query(ids[1]).manchester
    assert get_query(ids[2]).manchester.startswith("MetropolianCity")


def test_query_selection_follows_topic():
    christmas = select_queries("Christmas", "family dinner")
    netflix = select_queries("Netflix", "the app is slow")
    paris = select_queries("Paris", "we walked along the river")
    assert [query.id for query in christmas] == [
        "q1_americans_not_celebrating_christmas",
        "q5_america_recognizes_christmas",
    ]
    assert {query.id for query in netflix} == {
        "q2_positive_netflix_reviews",
        "q3_netflix_cities",
        "q4_netflix_offered_content",
    }
    assert paris == []


def test_user_prompts_match_report():
    assert "why Americans love to celebrate Christmas" in USER_PROMPTS["prompt_christmas"]
    assert "why people dislike Netflix" in USER_PROMPTS["prompt_netflix"]


def test_missing_ontology_is_reported_on_the_result(monkeypatch):
    monkeypatch.setattr(loader, "ONTOLOGY_PATH", Path("/tmp/infoiag-missing.owl"))
    result = run_query(get_query("q1_americans_not_celebrating_christmas"))
    assert result["status"] == "error"
    assert result["rows"] == []


def test_project_ontology_returns_netflix_film():
    assert "projectOntology#" in ONTOLOGY_IRI
    _load.cache_clear()
    try:
        offered = run_query(get_query("q4_netflix_offered_content"))
        holiday = run_query(get_query("q5_america_recognizes_christmas"))
        names = list_class_names()
    finally:
        _load.cache_clear()
    assert offered["status"] == "ok", offered["detail"]
    assert {"content": "theNotebookFilm", "genre": "romanceGenre"} in offered["rows"]
    assert holiday["status"] == "ok", holiday["detail"]
    assert {"country": "america", "holiday": "christmas"} in holiday["rows"]
    assert "Person" in names
    assert "MediaContent" in names


def test_divsumm_topics_have_thirty_tweets_per_group():
    for topic in ("Christmas", "Paris", "Netflix"):
        documents = load_documents(DATA_RAW / "divsumm" / "input_docs" / f"{topic}.txt")
        assert len(documents) == 90
        assert {document["topic"] for document in documents} == {topic}
        counts = {group: 0 for group in ("White", "Hisp", "AA")}
        for document in documents:
            counts[document["group"]] += 1
        assert counts == {"White": 30, "Hisp": 30, "AA": 30}
        assert len(load_reference_summaries(topic)) == 2
    christmas = load_documents(DATA_RAW / "divsumm" / "input_docs" / "Christmas.txt")
    assert all("&amp;" not in document["text"] for document in christmas)
