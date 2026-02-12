from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.knowledge.chunker import chunk_markdown, chunk_text

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    source: str
    chunk_id: str
    heading: str = ""
    score: float = 0.0


def load_knowledge(knowledge_dir: str, chunk_max_tokens: int = 300) -> list[Chunk]:
    """Load all knowledge files from the given directory."""
    knowledge_path = Path(knowledge_dir)
    if not knowledge_path.exists():
        logger.warning("Knowledge directory not found: %s", knowledge_dir)
        return []

    chunks: list[Chunk] = []

    for filepath in sorted(knowledge_path.iterdir()):
        if filepath.name.startswith(".") or filepath.name == "README.md":
            continue
        try:
            if filepath.suffix == ".json":
                chunks.extend(_load_json_faq(filepath))
            elif filepath.suffix == ".md":
                chunks.extend(_load_markdown(filepath, chunk_max_tokens))
            elif filepath.suffix == ".txt":
                chunks.extend(_load_text(filepath, chunk_max_tokens))
        except Exception:
            logger.exception("Failed to load %s", filepath)

    logger.info("Loaded %d chunks from %s", len(chunks), knowledge_dir)
    return chunks


def _load_json_faq(filepath: Path) -> list[Chunk]:
    """Load FAQ-format JSON: array of {q, a, tags?}."""
    data = json.loads(filepath.read_text(encoding="utf-8"))
    chunks = []
    for i, item in enumerate(data):
        q = item.get("q", "")
        a = item.get("a", "")
        tags = item.get("tags", [])
        text = f"Q: {q}\nA: {a}"
        if tags:
            text += f"\nTags: {', '.join(tags)}"
        chunks.append(Chunk(
            text=text,
            source=filepath.name,
            chunk_id=f"{filepath.name}:{i}",
            heading=q,
        ))
    return chunks


def _load_markdown(filepath: Path, max_tokens: int) -> list[Chunk]:
    """Load a markdown file and chunk by headings."""
    content = filepath.read_text(encoding="utf-8")
    raw_chunks = chunk_markdown(content, max_tokens)
    return [
        Chunk(
            text=text,
            source=filepath.name,
            chunk_id=f"{filepath.name}:{heading}:{i}",
            heading=heading,
        )
        for i, (heading, text) in enumerate(raw_chunks)
    ]


def _load_text(filepath: Path, max_tokens: int) -> list[Chunk]:
    """Load a text file and chunk by paragraphs."""
    content = filepath.read_text(encoding="utf-8")
    raw_chunks = chunk_text(content, max_tokens)
    return [
        Chunk(
            text=text,
            source=filepath.name,
            chunk_id=f"{filepath.name}:{i}",
        )
        for i, text in enumerate(raw_chunks)
    ]
