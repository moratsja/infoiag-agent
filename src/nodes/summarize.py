from src.llm.model import complete
from src.nodes.extract import format_documents

def summarize(state):
    summary = complete("", _user_message(state))
    return {"summary": summary, "trace": ["summarize"]}

def _user_message(state):
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
