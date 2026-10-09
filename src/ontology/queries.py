
from __future__ import annotations

from dataclasses import dataclass

from src.config import ONTOLOGY_IRI


@dataclass(frozen=True)
class OntologyQuery:
    id: str
    title: str
    description: str
    manchester: str
    sparql: str
    topics: tuple[str, ...]
    triggers: tuple[str, ...]
    agent_use: str
    owl_vs_db: str


def _prefix() -> str:
    return f"PREFIX : <{ONTOLOGY_IRI}>\n"


QUERIES: tuple[OntologyQuery, ...] = (
    OntologyQuery(
        id="q1_americans_not_celebrating_christmas",
        title="Americans who do not celebrate Christmas",
        description=(
            "People who are citizens of America and are not participants in Christmas. "
            "A hit is evidence against the assumption that all Americans celebrate Christmas."
        ),
        manchester=(
            "Person and (isCitizenOf value America) and "
            "not (isParticipantOf value christmas)"
        ),
        sparql=_prefix()
        + """SELECT ?person WHERE {
        ?person a :Person ;
                :isCitizenOf :America .
        FILTER NOT EXISTS { :christmas :hasParticipant ?person . }
        }""",
        topics=("Christmas",),
        triggers=("christmas", "american"),
        agent_use=(
            "Prompt 1 asks why Americans love to celebrate Christmas. "
            "If this query returns someone, the summary must not say that Americans in general celebrate it."
        ),
        owl_vs_db=(
            "In OWL, `not (isParticipantOf value christmas)` is open-world: an individual is in the class "
            "only if the reasoner can prove they are not a participant. A database or SPARQL "
            "`FILTER NOT EXISTS` treats missing triples as false. An empty Protégé result can therefore "
            "mean 'not provable', while SPARQL means 'no matching stored row'. "
            "The current file stores participation as hasParticipant from the event to the person, "
            "and it has no citizen who is a non-participant, so this query returns no rows."
        ),
    ),
    OntologyQuery(
        id="q5_america_recognizes_christmas",
        title="Public holiday recognized by America",
        description=(
            "Holidays that the country individual america recognizes. "
            "In ontologyStefan.rdf that holiday is christmas."
        ),
        manchester="america and (recognizesPublicHoliday value christmas)",
        sparql=_prefix()
        + """SELECT ?country ?holiday WHERE {
  ?country :recognizesPublicHoliday ?holiday .
}""",
        topics=("Christmas",),
        triggers=("christmas", "america"),
        agent_use=(
            "Prompt 1 asks why Americans love to celebrate Christmas. "
            "This query only shows that the country recognizes the holiday. "
            "A summary that says Americans in general love or celebrate it overclaims that fact."
        ),
        owl_vs_db=(
            "recognizesPublicHoliday has domain Country and range PublicHolidayEvent. "
            "christmas is stored as a PublicHolidayEvent, so the reasoner accepts the link. "
            "The query returns a country-level recognition. It does not return a citizen, "
            "a feeling, or proof that every American celebrates."
        ),
    ),
)


def get_query(query_id: str) -> OntologyQuery:
    for query in QUERIES:
        if query.id == query_id:
            return query
    known = ", ".join(query.id for query in QUERIES)
    raise KeyError(f"Unknown query {query_id!r}. Known queries: {known}")


def select_queries(topic: str, text: str) -> list[OntologyQuery]:
    # A query is included when the topic matches, or when one of its trigger words is in the text.
    blob = f"{topic}\n{text}".lower()
    selected: list[OntologyQuery] = []
    for query in QUERIES:
        topic_match = topic.lower() in {name.lower() for name in query.topics}
        trigger_match = any(trigger in blob for trigger in query.triggers)
        if topic_match or trigger_match:
            selected.append(query)
    return selected
