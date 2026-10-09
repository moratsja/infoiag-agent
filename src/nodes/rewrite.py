# One rewrite of the summary. The graph then extracts claims and checks again.

from __future__ import annotations

import json

from src.graph.state import AgentState
from src.llm.model import AGENT_SYSTEM_PROMPT, complete
from src.nodes.extract import format_documents


def rewrite(state: AgentState) -> dict:
    user = "\n".join(
        [
            f"Topic: {state['topic']}",
            f"User request: {state['user_prompt']}",
            f"Write exactly {state['k']} sentences.",
            "",
            "Current summary:",
            state["summary"],
            "",
            "Extracted claims:",
            json.dumps(state.get("claims") or [], ensure_ascii=False, indent=2),
            "",
            "Claim checks (SUPPORTED, CONTRADICTED, or NOT_VERIFIABLE):",
            json.dumps(state.get("claim_evaluations") or [], ensure_ascii=False, indent=2),
            "",
            "Problems to fix:",
            json.dumps(state["issues"], ensure_ascii=False, indent=2),
            "",
            "Ontology query results:",
            json.dumps(state["query_results"], ensure_ascii=False, indent=2),
            "",
            "Posts:",
            format_documents(state["documents"]),
            "",
            "Rewrite the summary.",
            "Keep information that the posts support.",
            "Delete any sentence that says Americans celebrate Christmas or Americans love Christmas.",
            "Replace it with what the posts actually contain, including enjoyment, complaints, and ordinary mentions.",
            "Keep ontology facts that the check marked SUPPORTED.",
            "Do not invent facts.",
            "Do not turn a loaded premise in the user request into a statement about everyone.",
            "Return only the revised summary.",
        ]
    )
    revised = complete(AGENT_SYSTEM_PROMPT, user)
    return {
        "summary": revised,
        "revision": state["revision"] + 1,
        "trace": ["rewrite"],
    }
