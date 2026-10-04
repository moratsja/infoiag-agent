"""Chat model factory and the system prompts used by the agent and the baseline."""

from __future__ import annotations

import os
import re

from src.config import (
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    OLLAMA_BASE_URL,
    OPENAI_MODEL,
)

AGENT_SYSTEM_PROMPT = """You summarise dialect-diverse social media posts from the DivSumm dataset.
The posts are labelled with a social group: White, Hisp (Hispanic), or AA (African-American).

Write an abstractive summary that stays grounded in the posts.
Represent views from every group that appears in the input. Do not treat one group's perspective as the view of everyone.
If the user asks for only one side (why people love something, or why people dislike something), still report contrary evidence that is present in the posts or in the ontology context, and present it as a differing view.

Ontology context is a constraint, not optional colour:
- If a query returns a counterexample, do not make the universal claim that counterexample contradicts.
- If a query did not run, or returned no rows, that is not evidence that a universal claim is true.
- Do not invent places, facilities, participation, or company facts that are absent from both the posts and the ontology context.
"""

BASELINE_SYSTEM_PROMPT = """You summarise social media posts.
Follow the user request and write an abstractive summary grounded in the posts.
"""


def get_chat_model():
    """Return the configured chat model. Imports the provider only when called."""
    provider = LLM_PROVIDER.lower()
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=LLM_TEMPERATURE,
        )
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is empty. Set it in .env or switch LLM_PROVIDER=ollama.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=OPENAI_MODEL, temperature=LLM_TEMPERATURE)
    raise RuntimeError(f"Unknown LLM_PROVIDER {provider!r}. Use 'ollama' or 'openai'.")


def complete(system: str, user: str) -> str:
    """Run one system/user completion and return plain text."""
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
