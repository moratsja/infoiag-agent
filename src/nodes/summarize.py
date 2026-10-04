"""Generate the first summary.

Input: tweets, the user prompt, and (in agent mode) ontology query results.
Output: ``summary``, a string of about ``k`` sentences.
"""

from __future__ import annotations

import json

from src.graph.state import AgentState
from src.llm.model import AGENT_SYSTEM_PROMPT, BASELINE_SYSTEM_PROMPT, complete
from src.nodes.extract import format_documents


def summarize(state: AgentState) -> dict:
    system = BASELINE_SYSTEM_PROMPT if state["mode"] == "baseline" else AGENT_SYSTEM_PROMPT
    user = _user_message(state)
    summary = complete(system, user)
    return {"summary": summary, "trace": ["summarize"]}


def _user_message(state: AgentState) -> str:
    tweets = format_documents(state["documents"])
    parts = [
        f"Topic: {state['topic']}",
        f"User request: {state['user_prompt']}",
        f"Write exactly {state['k']} sentences.",
        "",
        "Posts:",
        tweets,
    ]
    if state["mode"] == "agent":
        parts.extend(
            [
                "",
                "Ontology context (query id, status, rows):",
                json.dumps(state["ontology_context"], ensure_ascii=False, indent=2),
            ]
        )
    return "\n".join(parts)
