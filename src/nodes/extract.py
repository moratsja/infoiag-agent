"""Extract structure from the source tweets and from the generated summary.

Extraction is lexical on purpose: the assignment allows simple NLP here,
and this step has to stay available when the ontology check runs again
after a rewrite.
"""

from __future__ import annotations

import re

from src.config import MAX_TWEETS
from src.graph.state import AgentState

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def format_documents(documents: list[dict[str, str]], limit: int = MAX_TWEETS) -> str:
    """Render tweets with their DivSumm group label."""
    lines = [f"[{index}] ({doc['group']}) {doc['text']}" for index, doc in enumerate(documents[:limit], start=1)]
    hidden = len(documents) - limit
    if hidden > 0:
        lines.append(f"... {hidden} tweets omitted by MAX_TWEETS.")
    return "\n".join(lines)


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT.split(text.strip()) if part.strip()]


def extract_input(state: AgentState) -> dict:
    """Collect group counts and the raw tweet text used to choose ontology queries."""
    counts: dict[str, int] = {}
    for doc in state["documents"]:
        counts[doc["group"]] = counts.get(doc["group"], 0) + 1
    return {
        "extracted_input": {
            "group_counts": counts,
            "text": format_documents(state["documents"]),
        },
        "trace": ["extract_input"],
    }


def extract_summary(state: AgentState) -> dict:
    """Split the current summary into sentences before the ontology check."""
    return {
        "summary_sentences": split_sentences(state["summary"]),
        "trace": ["extract_summary"],
    }
