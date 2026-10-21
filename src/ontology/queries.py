from dataclasses import dataclass

from src.config import ONTOLOGY_IRI

@dataclass(frozen=True)
class OntologyQuery:
    id: str
    title: str
    manchester: str
    sparql: str
    topics: tuple[str, ...]
    triggers: tuple[str, ...]

def _prefix():
    return f"PREFIX : <{ONTOLOGY_IRI}>\n"

QUERIES = (
    OntologyQuery(
        id="q1",
        title="Americans who do not celebrate Christmas",
        manchester="Person and (isCitizenOf value America) and not (isParticipantOf value christmas)",
        sparql=_prefix()
        + """SELECT ?person WHERE {
        ?person a :Person ;
                :isCitizenOf :America .
        FILTER NOT EXISTS { :christmas :hasParticipant ?person . }
        }""",
        topics=("Christmas",),
        triggers=("christmas", "american"),
    ),
    OntologyQuery(
        id="q2",
        title="Public holiday recognized by America",
        manchester="america and (recognizesPublicHoliday value christmas)",
        sparql=_prefix()
        + """SELECT ?country ?holiday WHERE {
  ?country :recognizesPublicHoliday ?holiday .

}""",
        topics=("Christmas",),
        triggers=("christmas", "america"),
    ),
)

def get_query(query_id):
    for query in QUERIES:
        if query.id == query_id:
            return query
    known = ", ".join(query.id for query in QUERIES)
    raise KeyError(f"Unknown query {query_id!r}. Known queries: {known}")

def select_queries(topic, text):
    blob = f"{topic}\n{text}".lower()
    selected = []
    for query in QUERIES:
        topic_match = topic.lower() in {name.lower() for name in query.topics}
        trigger_match = any(trigger in blob for trigger in query.triggers)
        if topic_match or trigger_match:
            selected.append(query)
    return selected
