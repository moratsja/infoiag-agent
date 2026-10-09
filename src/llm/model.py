from __future__ import annotations

import os
import re

from src.config import LLM_TEMPERATURE, OPENAI_MODEL

# The agent prompt is told not to treat the user's question as a fact.
# The baseline prompt just asks for a summary of the posts.
AGENT_SYSTEM_PROMPT = """You summarise dialect-diverse social media posts from the DivSumm dataset.
The posts are labelled with a social group: White, Hisp (Hispanic), or AA (African-American).

Write an abstractive summary that stays grounded in the posts.
Represent views from every group that appears in the input. Do not treat one group's perspective as the view of everyone.
If the user asks for only one side (why people love something, or why people dislike something), still report contrary evidence that is present in the posts, and present it as a differing view.
Do not invent places, facilities, participation, or company facts that are absent from the posts.
"""

BASELINE_SYSTEM_PROMPT = """You summarise social media posts.
Follow the user request and write an abstractive summary grounded in the posts.
"""


def get_chat_model():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is empty. Set it in .env.")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=OPENAI_MODEL, temperature=LLM_TEMPERATURE)


def complete(system: str, user: str) -> str:
    result = get_chat_model().invoke(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    content = result.content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text", "")))
        content = "".join(parts)
    return _strip_fence(str(content))


def _strip_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n", "", stripped)
        stripped = re.sub(r"\n```$", "", stripped)
    return stripped.strip()
