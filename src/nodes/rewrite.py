# One rewrite of the summary. The graph then extracts claims and checks again.


import json

from src.llm.model import complete
from src.nodes.extract import format_documents


def rewrite(state):
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
            "Fix the claims marked CONTRADICTED, using the query results.",
            "Keep claims marked SUPPORTED.",
            "Leave NOT_VERIFIABLE claims as they are.",
            "Stay with what the posts say. Do not invent facts.",
            "Return only the revised summary.",
        ]
    )
    revised = complete("", user)
    return {
        "summary": revised,
        "revision": state["revision"] + 1,
        "trace": ["rewrite"],
    }
