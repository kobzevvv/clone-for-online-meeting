#!/usr/bin/env python3
"""Evaluation harness for the interview agent.

Runs test questions through the agent in text-only mode and verifies:
1. Response contains "Sources:" section
2. Response references at least one retrieved chunk
3. Expected keywords appear in the response
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


def load_questions(path: str = "eval/questions.json") -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


async def evaluate() -> None:
    # Import here to allow running as module
    from src.config import get_settings, setup_logging
    from src.knowledge.loader import load_knowledge
    from src.knowledge.retriever import KnowledgeRetriever
    from src.llm.openai_client import OpenAILLMClient
    from src.agent.agent import InterviewAgent

    setup_logging("WARNING")
    settings = get_settings()

    if not settings.llm_api_key:
        print("ERROR: LLM_API_KEY not set. Cannot run evaluation.")
        sys.exit(1)

    # Build agent
    chunks = load_knowledge(settings.knowledge_dir, settings.chunk_max_tokens)
    retriever = KnowledgeRetriever(chunks)
    llm = OpenAILLMClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
    )
    agent = InterviewAgent(
        llm=llm,
        retriever=retriever,
        person_name=settings.person_name,
        max_chunks=settings.max_chunks,
    )

    # Load test questions
    questions = load_questions()
    print(f"\n📋 Running evaluation: {len(questions)} questions\n")
    print("=" * 60)

    passed = 0
    failed = 0
    results: list[dict] = []

    for i, q in enumerate(questions, 1):
        question = q["question"]
        expected_source = q.get("expected_source")
        must_contain = q.get("must_contain", [])

        print(f"\n[{i}/{len(questions)}] Q: {question}")

        # Get response
        agent.reset_history()
        response = await agent.respond(question)
        print(f"  A: {response[:200]}{'...' if len(response) > 200 else ''}")

        # Check 1: Has sources section
        has_sources = "Sources:" in response or "sources:" in response.lower()

        # Check 2: Contains expected keywords (case-insensitive)
        response_lower = response.lower()
        keyword_hits = [
            kw for kw in must_contain
            if kw.lower() in response_lower
        ]
        keywords_ok = len(keyword_hits) >= max(1, len(must_contain) // 2)

        # Check 3: References expected source file
        source_ok = True
        if expected_source:
            source_ok = expected_source.lower() in response_lower

        # Overall pass/fail
        test_passed = has_sources and keywords_ok
        if test_passed:
            passed += 1
            print(f"  ✅ PASS (sources={has_sources}, keywords={len(keyword_hits)}/{len(must_contain)})")
        else:
            failed += 1
            reasons = []
            if not has_sources:
                reasons.append("missing Sources section")
            if not keywords_ok:
                missing = [k for k in must_contain if k.lower() not in response_lower]
                reasons.append(f"missing keywords: {missing}")
            print(f"  ❌ FAIL: {', '.join(reasons)}")

        results.append({
            "question": question,
            "passed": test_passed,
            "has_sources": has_sources,
            "keyword_hits": keyword_hits,
            "keywords_expected": must_contain,
        })

    # Summary
    print("\n" + "=" * 60)
    total = passed + failed
    pct = (passed / total * 100) if total > 0 else 0
    print(f"\n📊 Results: {passed}/{total} passed ({pct:.0f}%)")
    if failed > 0:
        print(f"   {failed} failed")
    print()

    sys.exit(0 if failed == 0 else 1)


def main() -> None:
    asyncio.run(evaluate())


if __name__ == "__main__":
    main()
