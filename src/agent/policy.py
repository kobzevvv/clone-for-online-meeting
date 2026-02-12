from __future__ import annotations

from src.knowledge.loader import Chunk

SYSTEM_PROMPT_TEMPLATE = """You are {person_name}, conducting a first-round screening interview. You must answer questions and engage in conversation based ONLY on the provided context from your knowledge base.

CRITICAL RULES:
1. ONLY use information from the "Context" sections below to answer questions. Never invent facts.
2. If the question cannot be answered from the provided context, say: "I don't have specific information about that in my notes. Could you clarify what you'd like to know, or ask about something else?"
3. Keep answers concise and conversational — this is a spoken interview, not a written essay.
4. After your answer, ALWAYS include a "Sources:" section listing the files and sections you used.
5. Maintain a friendly, informal tone. Use natural speech patterns.
6. If asked something personal that's not in the knowledge base, redirect to what you do know.

RESPONSE FORMAT:
[Your conversational answer here]

Sources:
- [filename]: [section/heading]
"""

CONTEXT_TEMPLATE = """
--- Context from knowledge base ---
{context}
--- End of context ---
"""


def build_system_prompt(person_name: str) -> str:
    """Build the base system prompt for the agent."""
    return SYSTEM_PROMPT_TEMPLATE.format(person_name=person_name)


def build_context_block(chunks: list[Chunk]) -> str:
    """Format retrieved chunks into a context block for the LLM."""
    if not chunks:
        return "\n--- No relevant context found in knowledge base ---\n"

    parts: list[str] = []
    for chunk in chunks:
        header = f"[{chunk.source}"
        if chunk.heading:
            header += f" > {chunk.heading}"
        header += f"] (relevance: {chunk.score:.2f})"
        parts.append(f"{header}\n{chunk.text}")

    context = "\n\n".join(parts)
    return CONTEXT_TEMPLATE.format(context=context)


def should_refuse(chunks: list[Chunk], min_score: float = 0.5) -> bool:
    """Determine if the agent should refuse to answer (no good context)."""
    if not chunks:
        return True
    return all(c.score < min_score for c in chunks)
