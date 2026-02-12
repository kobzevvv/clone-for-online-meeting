from __future__ import annotations

import logging

import numpy as np
from rank_bm25 import BM25Okapi

from src.knowledge.loader import Chunk

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """BM25-based retriever over knowledge chunks."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        tokenized = [self._tokenize(c.text) for c in chunks]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None
        logger.info("Indexed %d chunks for retrieval", len(chunks))

    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]:
        """Return the top-k most relevant chunks for the query."""
        if not self.chunks or self.bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                chunk = Chunk(
                    text=self.chunks[idx].text,
                    source=self.chunks[idx].source,
                    chunk_id=self.chunks[idx].chunk_id,
                    heading=self.chunks[idx].heading,
                    score=float(scores[idx]),
                )
                results.append(chunk)

        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + lowercase tokenization."""
        return text.lower().split()
