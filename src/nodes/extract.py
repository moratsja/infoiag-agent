from __future__ import annotations

import re

from src.config import MAX_TWEETS
from src.graph.state import AgentState

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def format_documents(documents: list[dict[str, str]], limit: int = MAX_TWEETS) -> str:
    # Each line is [n] (group) tweet, so the model can see which group said what.
    lines = [f"[{index}] ({doc['group']}) {doc['text']}" for index, doc in enumerate(documents[:limit], start=1)]
    hidden = len(documents) - limit
    if hidden > 0:
        lines.append(f"... {hidden} tweets omitted by MAX_TWEETS.")
    return "\n".join(lines)


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT.split(text.strip()) if part.strip()]


def extract_summary(state: AgentState) -> dict:
    # Not a graph node anymore. Tests still call it.
    return {
        "summary_sentences": split_sentences(state["summary"]),
        "trace": ["extract_summary"],
    }
