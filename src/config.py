"""Paths, model settings, and the two user prompts from Intermediate Report 1."""

from __future__ import annotations

import csv
import html
import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DIVSUMM_DIR = DATA_RAW / "divsumm"

load_dotenv(ROOT / ".env")

GROUPS = ("White", "Hisp", "AA")

# User prompts from Intermediate Report 1, section 2. Applied to each topic.
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


def env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


LLM_PROVIDER = env_str("LLM_PROVIDER", "ollama")
LLM_MODEL = env_str("LLM_MODEL", "llama3.1")
LLM_TEMPERATURE = env_float("LLM_TEMPERATURE", 0.7)
OLLAMA_BASE_URL = env_str("OLLAMA_BASE_URL", "http://localhost:11434")
OPENAI_MODEL = env_str("OPENAI_MODEL", "gpt-4o")
ONTOLOGY_IRI = env_str(
    "ONTOLOGY_IRI",
    "http://www.semanticweb.org/ewill/ontologies/2026/8/projectOntology#",
)
def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


ONTOLOGY_PATH = _resolve(
    env_str("ONTOLOGY_FILE", str(ROOT / "ontology" / "ontologyStefan.rdf"))
)
MAX_REVISIONS = env_int("MAX_REVISIONS", 1)
SUMMARY_SENTENCES = env_int("SUMMARY_SENTENCES", 5)
MAX_TWEETS = env_int("MAX_TWEETS", 90)


def load_documents(path: Path) -> list[dict[str, str]]:
    """Load tweets as ``{text, group, topic}``.

    ``group`` is one of White, Hisp, or AA, matching DivSumm.
    A ``.txt`` file is a DivSumm input document (group, tab, tweet).
    A ``.json`` file is a list of those objects, or ``{"tweets": [...]}``.
    """
    documents = _load_divsumm_txt(path) if path.suffix.lower() == ".txt" else _load_json(path)
    if not documents:
        raise ValueError(f"No tweets in {path}")
    return documents


def load_reference_summaries(topic: str) -> list[dict[str, str]]:
    """Load the two human abstractive summaries for a DivSumm topic."""
    folder = DIVSUMM_DIR / "abstractive"
    paths = sorted(folder.glob(f"{topic}_Annotat*.txt"))
    summaries: list[dict[str, str]] = []
    for path in paths:
        text = _read_divsumm_text(path).replace("\r\n", "\n").strip()
        summaries.append({"annotator": path.stem, "text": text})
    return summaries


def _load_json(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["tweets"] if isinstance(payload, dict) else payload
    return [_document(row["group"], row["text"], row.get("topic", "")) for row in rows]


def _load_divsumm_txt(path: Path) -> list[dict[str, str]]:
    topic = path.stem
    documents: list[dict[str, str]] = []
    for row in csv.reader(_read_divsumm_text(path).splitlines(), delimiter="\t", quotechar='"'):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) != 2:
            raise ValueError(f"Expected group and tweet text in {path}, got {row!r}")
        documents.append(_document(row[0], row[1], topic))
    return documents


def _document(group: str, text: str, topic: str) -> dict[str, str]:
    group = group.strip()
    if group not in GROUPS:
        raise ValueError(f"Unknown group {group!r}; expected one of {GROUPS}")
    return {"text": html.unescape(str(text)).strip(), "group": group, "topic": str(topic).strip()}


def _read_divsumm_text(path: Path) -> str:
    """DivSumm files are Windows-1252, not UTF-8."""
    return path.read_bytes().decode("cp1252")
