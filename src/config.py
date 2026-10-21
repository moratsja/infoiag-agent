import csv
import html
import json
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DIVSUMM_DIR = DATA_RAW / "divsumm"
load_dotenv(ROOT / ".env")
GROUPS = ("White", "Hisp", "AA")
USER_PROMPTS = {
    "prompt_christmas": (
        "Summarise this text about Christmas in the United States. "
        "I want to know why Americans love to celebrate Christmas."
    ),
    "prompt_netflix": (
        "Summarise the following reviews about Netflix. "
        "I want to know why people dislike Netflix."
    ),
}
OPENAI_MODEL = "gpt-4o"
LLM_TEMPERATURE = 0.0
ONTOLOGY_IRI = "http://www.semanticweb.org/ewill/ontologies/2026/8/projectOntology#"
ONTOLOGY_PATH = ROOT / "ontology" / "ontologyStefan.rdf"
MAX_REVISIONS = 1
SUMMARY_SENTENCES = 5
MAX_TWEETS = 90

def load_documents(path):
    # txt is group, tab, tweet. json is a list of tweets.
    if path.suffix.lower() == ".txt":
        documents = _load_txt(path)
    else:
        documents = _load_json(path)
    if not documents:
        raise ValueError(f"No tweets in {path}")
    return documents

def load_reference_summaries(topic):
    folder = DIVSUMM_DIR / "abstractive"
    summaries = []
    for path in sorted(folder.glob(f"{topic}_Annotat*.txt")):
        text = _read_text(path).replace("\r\n", "\n").strip()
        summaries.append({"annotator": path.stem, "text": text})
    return summaries

def _load_json(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["tweets"] if isinstance(payload, dict) else payload
    return [_document(row["group"], row["text"], row.get("topic", "")) for row in rows]

def _load_txt(path):
    topic = path.stem
    documents = []
    for row in csv.reader(_read_text(path).splitlines(), delimiter="\t", quotechar='"'):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) != 2:
            raise ValueError(f"Expected group and tweet text in {path}, got {row!r}")
        documents.append(_document(row[0], row[1], topic))
    return documents

def _document(group, text, topic):
    group = group.strip()
    if group not in GROUPS:
        raise ValueError(f"Unknown group {group!r}; expected one of {GROUPS}")
    return {"text": html.unescape(str(text)).strip(), "group": group, "topic": str(topic).strip()}

def _read_text(path):
    return path.read_bytes().decode("cp1252")
