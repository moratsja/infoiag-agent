"""DL queries from Intermediate Report 1, section 3.

Manchester syntax is the form you already ran in Protégé. The SPARQL strings
are a closed-world stand-in so the agent can run without a Java reasoner.
Local names and the ontology IRI must match the Protégé file. OWL negation is
open-world: an empty SPARQL result is not the same inference Protégé makes
with ``not (...)``.
"""

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
            "Ontology2809eva.rdf stores participation as hasParticipant from the event to the person, "
            "and it does not yet contain the individuals America or christmas, so this query returns no rows."
        ),
    ),
    OntologyQuery(
        id="q2_positive_netflix_reviews",
        title="Positive Netflix reviews",
        description=(
            "Reviews of Netflix that the ontology marks as positive. "
            "A hit is a positive perspective the summary should not drop."
        ),
        manchester=(
            "Review and (isReviewOf value Netflix) and (hasPositiveContent value true)"
        ),
        sparql=_prefix()
        + """SELECT ?review WHERE {
  ?review a :Review ;
          :hasPositiveContent ?positive .
  FILTER(LCASE(STR(?positive)) IN ("true", "1"))
  { ?review :isReviewOf :Netflix . }
  UNION
  { ?review :isReviewOf :netflixService . }
  UNION
  { :netflixService :hasReview ?review . }
}""",
        topics=("Netflix",),
        triggers=("netflix", "review"),
        agent_use=(
            "Prompt 2 asks why people dislike Netflix. "
            "If this query returns a review, the summary must not present dislike as the only view."
        ),
        owl_vs_db=(
            "The class expression relies on the reasoner to classify reviews under Review "
            "and to read the data property hasPositiveContent. A database query only returns rows "
            "you stored as positive; it would not classify a review through subclass or property inference."
        ),
    ),
    OntologyQuery(
        id="q3_netflix_cities",
        title="Netflix cities",
        description=(
            "Metropolitan cities in which Netflix has a facility. "
            "Used to check facility claims in a summary against the knowledge base."
        ),
        manchester=(
            "MetropolianCity and (hasFacilityOf some "
            "(Company and (hasCompanyName value Netflix)))"
        ),
        sparql=_prefix()
        + """SELECT ?city WHERE {
  ?city a :MetropolianCity .
  ?company :hasFacilityIn ?city .
  { ?company :hasCompanyName :Netflix . }
  UNION
  { ?company :hasCompanyName "Netflix" . }
}""",
        topics=("Netflix",),
        triggers=("netflix", "facility", "office"),
        agent_use=(
            "If the summary names a Netflix facility in a city outside this result, "
            "that place claim is not supported by the ontology."
        ),
        owl_vs_db=(
            "`hasFacilityOf some (Company and ...)` is an existential restriction. "
            "The reasoner can return a city when the company link is inferred. "
            "The class name MetropolianCity follows the spelling in Intermediate Report 1. "
            "In Ontology2809eva.rdf the property runs from the company to the city and is named hasFacilityIn. "
            "An empty result does not prove that no such city exists, because OWL does not "
            "treat missing facts as false. The file has no Netflix facility yet."
        ),
    ),
    OntologyQuery(
        id="q4_netflix_offered_content",
        title="Content offered by the Netflix service",
        description=(
            "Media offered by the individual netflixService, with genre when one is stored. "
            "This query matches individuals that are present in Ontology2809eva.rdf."
        ),
        manchester="netflixService and (offersContent some MediaContent)",
        sparql=_prefix()
        + """SELECT ?content ?genre WHERE {
  :netflixService :offersContent ?content .
  OPTIONAL { ?content :hasGenre ?genre . }
}""",
        topics=("Netflix",),
        triggers=("netflix",),
        agent_use=(
            "Gives the summarizer the media the ontology actually records for Netflix, "
            "including theNotebookFilm and romanceGenre."
        ),
        owl_vs_db=(
            "offersContent has domain Company or Service. netflixService is asserted as a Service, "
            "so a reasoner accepts the triple. A database would need that service row to exist; "
            "it would not accept the same triple through a union domain."
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
    """Pick the report queries that apply to this topic and text."""
    blob = f"{topic}\n{text}".lower()
    selected: list[OntologyQuery] = []
    for query in QUERIES:
        topic_match = topic.lower() in {name.lower() for name in query.topics}
        trigger_match = any(trigger in blob for trigger in query.triggers)
        if topic_match or trigger_match:
            selected.append(query)
    return selected
