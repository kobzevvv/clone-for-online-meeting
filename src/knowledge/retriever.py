from __future__ import annotations

import logging
import re

import numpy as np
from rank_bm25 import BM25Okapi

from src.knowledge.loader import Chunk

logger = logging.getLogger(__name__)


_STOP_WORDS = frozenset(
    "a an the is are was were be been being do does did will would shall should "
    "can could may might must have has had having get gets got to of in for on at "
    "by with from and or not no nor but if then else when where how what which who "
    "whom this that these those it its he she they we you i me him her us them my "
    "your his our their about as into through during before after above below up "
    "down out off over under again further once here there all each every both few "
    "more most other some such only own same so than too very just also now".split()
)


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
        """Lowercase tokenization with punctuation stripping and stop word removal."""
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]
