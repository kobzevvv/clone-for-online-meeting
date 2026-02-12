from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from src.llm.base import LLMClient

logger = logging.getLogger(__name__)


class OpenAILLMClient(LLMClient):
    """OpenAI-compatible LLM client with streaming."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None) -> None:
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1",
        )

    async def stream_completion(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        logger.debug("LLM request: %d messages, model=%s", len(messages), self.model)
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            stream=True,
            temperature=0.3,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
