"""Tests for the interview agent (mocked LLM)."""
import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from src.agent.agent import InterviewAgent
from src.agent.policy import build_system_prompt, build_context_block, should_refuse
from src.knowledge.loader import Chunk
from src.knowledge.retriever import KnowledgeRetriever
from src.llm.base import LLMClient


class MockLLM(LLMClient):
    """Mock LLM that returns a fixed response."""

    def __init__(self, response: str = "Test response.\n\nSources:\n- test.md: Section") -> None:
        self.response = response
        self.last_messages: list[dict[str, str]] = []

    async def stream_completion(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        self.last_messages = messages
        for word in self.response.split(" "):
            yield word + " "


def _make_agent(response: str | None = None) -> InterviewAgent:
    chunks = [
        Chunk(text="Improvado is a B2B company.", source="faq.json", chunk_id="faq:0", heading="About"),
        Chunk(text="The tech stack includes Python.", source="guide.md", chunk_id="guide:0", heading="Tech"),
    ]
    retriever = KnowledgeRetriever(chunks)
    llm = MockLLM(response=response or "Improvado is a B2B company.\n\nSources:\n- faq.json: About")
    return InterviewAgent(llm=llm, retriever=retriever, person_name="Daniel")


@pytest.mark.asyncio
async def test_agent_respond():
    agent = _make_agent()
    response = await agent.respond("What is Improvado?")
    assert "Improvado" in response
    assert "Sources" in response


@pytest.mark.asyncio
async def test_agent_streaming():
    agent = _make_agent()
    tokens = []
    async for token in agent.respond_stream("Tell me about the tech stack"):
        tokens.append(token)
    assert len(tokens) > 0
    full = "".join(tokens)
    assert "Sources" in full


def test_build_system_prompt():
    prompt = build_system_prompt("Daniel")
    assert "Daniel" in prompt
    assert "knowledge base" in prompt.lower()


def test_build_context_block():
    chunks = [
        Chunk(text="Test content", source="test.md", chunk_id="test:0", heading="Title", score=1.5),
    ]
    block = build_context_block(chunks)
    assert "test.md" in block
    assert "Test content" in block


def test_should_refuse_no_chunks():
    assert should_refuse([]) is True


def test_should_refuse_low_scores():
    chunks = [Chunk(text="x", source="x", chunk_id="x", score=0.1)]
    assert should_refuse(chunks, min_score=0.5) is True


def test_should_not_refuse_good_scores():
    chunks = [Chunk(text="x", source="x", chunk_id="x", score=2.0)]
    assert should_refuse(chunks, min_score=0.5) is False
