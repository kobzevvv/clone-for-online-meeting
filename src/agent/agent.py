from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator

from src.agent.policy import build_context_block, build_stage_hint, build_system_prompt
from src.knowledge.loader import Chunk
from src.knowledge.retriever import KnowledgeRetriever
from src.llm.base import LLMClient

logger = logging.getLogger(__name__)


class InterviewAgent:
    """Knowledge-grounded interview agent.

    Retrieves relevant context from the knowledge base, then uses
    an LLM to generate grounded responses with source citations.
    """

    def __init__(
        self,
        llm: LLMClient,
        retriever: KnowledgeRetriever,
        person_name: str = "Daniel",
        max_chunks: int = 5,
    ) -> None:
        self.llm = llm
        self.retriever = retriever
        self.person_name = person_name
        self.max_chunks = max_chunks
        self.system_prompt = build_system_prompt(person_name)
        self.conversation_history: list[dict[str, str]] = []

    def _count_exchanges(self) -> int:
        """Count completed exchanges (user+assistant pairs) in history."""
        return len(self.conversation_history) // 2

    async def respond(self, user_message: str) -> str:
        """Generate a complete (non-streaming) response."""
        parts: list[str] = []
        async for token in self.respond_stream(user_message):
            parts.append(token)
        return "".join(parts)

    async def respond_stream(self, user_message: str) -> AsyncIterator[str]:
        """Generate a streaming response to the user's message.

        Yields text tokens as they arrive from the LLM.
        Also logs latency metrics.
        """
        t_start = time.monotonic()

        # Retrieve relevant context
        chunks = self.retriever.retrieve(user_message, top_k=self.max_chunks)
        t_retrieval = time.monotonic()
        logger.info(
            "Retrieved %d chunks in %.0fms (top score: %.2f)",
            len(chunks),
            (t_retrieval - t_start) * 1000,
            chunks[0].score if chunks else 0,
        )

        # Build messages
        context_block = build_context_block(chunks)
        stage_hint = build_stage_hint(self._count_exchanges())
        messages = [
            {"role": "system", "content": self.system_prompt + context_block + stage_hint},
        ]
        # Add conversation history (keep last 10 turns for context)
        messages.extend(self.conversation_history[-10:])
        messages.append({"role": "user", "content": user_message})

        # Stream LLM response
        full_response: list[str] = []
        first_token = True
        async for token in self.llm.stream_completion(messages):
            if first_token:
                t_first = time.monotonic()
                logger.info(
                    "First token in %.0fms (retrieval: %.0fms, LLM TTFT: %.0fms)",
                    (t_first - t_start) * 1000,
                    (t_retrieval - t_start) * 1000,
                    (t_first - t_retrieval) * 1000,
                )
                first_token = False
            full_response.append(token)
            yield token

        # Update conversation history
        response_text = "".join(full_response)
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response_text})

        t_end = time.monotonic()
        logger.info("Full response in %.0fms", (t_end - t_start) * 1000)

    def reset_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
