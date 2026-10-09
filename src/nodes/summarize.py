# First summary is written from the tweets. The ontology check happens after this step.

from __future__ import annotations

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
    return "\n".join(
        [
            f"Topic: {state['topic']}",
            f"User request: {state['user_prompt']}",
            f"Write exactly {state['k']} sentences.",
            "",
            "Posts:",
            tweets,
        ]
    )
