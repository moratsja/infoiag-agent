import re

from src.config import MAX_TWEETS

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

def format_documents(documents, limit = MAX_TWEETS):
    # group stays on the tweet, the model only gets the text
    lines = [f"[{index}] {doc['text']}" for index, doc in enumerate(documents[:limit], start=1)]
    hidden = len(documents) - limit
    if hidden > 0:
        lines.append(f"... {hidden} tweets omitted by MAX_TWEETS.")
    return "\n".join(lines)

def split_sentences(text):
    return [part.strip() for part in _SENTENCE_SPLIT.split(text.strip()) if part.strip()]

def extract_summary(state):
    return {
        "summary_sentences": split_sentences(state["summary"]),
        "trace": ["extract_summary"],
    }
