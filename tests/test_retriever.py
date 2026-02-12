"""Tests for knowledge retrieval."""
from src.knowledge.loader import Chunk
from src.knowledge.retriever import KnowledgeRetriever


def _make_chunks() -> list[Chunk]:
    return [
        Chunk(
            text="Python is a programming language used for web development and data science.",
            source="test.md",
            chunk_id="test.md:0",
            heading="Python",
        ),
        Chunk(
            text="TypeScript adds static typing to JavaScript for better development experience.",
            source="test.md",
            chunk_id="test.md:1",
            heading="TypeScript",
        ),
        Chunk(
            text="Machine learning models can be trained on large datasets to make predictions.",
            source="test.md",
            chunk_id="test.md:2",
            heading="ML",
        ),
    ]


def test_retrieve_relevant():
    """Test that relevant chunks are retrieved."""
    chunks = _make_chunks()
    retriever = KnowledgeRetriever(chunks)
    results = retriever.retrieve("Python programming")
    assert len(results) > 0
    assert results[0].heading == "Python"
    assert results[0].score > 0


def test_retrieve_top_k():
    """Test top-k limiting."""
    chunks = _make_chunks()
    retriever = KnowledgeRetriever(chunks)
    results = retriever.retrieve("programming language", top_k=1)
    assert len(results) <= 1


def test_retrieve_no_match():
    """Test query with no relevant results."""
    chunks = _make_chunks()
    retriever = KnowledgeRetriever(chunks)
    results = retriever.retrieve("quantum physics black holes")
    # BM25 may still return results but with low scores
    if results:
        assert all(r.score < 1.0 for r in results)


def test_empty_retriever():
    """Test retriever with no chunks."""
    retriever = KnowledgeRetriever([])
    results = retriever.retrieve("anything")
    assert results == []
