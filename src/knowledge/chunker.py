from __future__ import annotations

import re


def chunk_markdown(text: str, max_tokens: int = 300) -> list[tuple[str, str]]:
    """Split markdown into (heading, content) chunks.

    Splits on headings (##, ###, etc.), then further splits long
    sections into smaller chunks at paragraph boundaries.
    Returns list of (heading, chunk_text) tuples.
    """
    sections: list[tuple[str, str]] = []
    current_heading = "Introduction"
    current_lines: list[str] = []

    for line in text.split("\n"):
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading_match:
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append((current_heading, body))
            current_heading = heading_match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_heading, body))

    # Further split long sections
    result: list[tuple[str, str]] = []
    for heading, body in sections:
        if _approx_tokens(body) <= max_tokens:
            result.append((heading, body))
        else:
            sub_chunks = _split_by_paragraphs(body, max_tokens)
            for i, chunk in enumerate(sub_chunks):
                label = heading if i == 0 else f"{heading} (cont.)"
                result.append((label, chunk))

    return result


def chunk_text(text: str, max_tokens: int = 300) -> list[str]:
    """Split plain text into chunks at paragraph boundaries."""
    return _split_by_paragraphs(text, max_tokens)


def _split_by_paragraphs(text: str, max_tokens: int) -> list[str]:
    """Split text into chunks not exceeding max_tokens, breaking at paragraph boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_len = _approx_tokens(para)
        if current and current_len + para_len > max_tokens:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _approx_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token for English."""
    return max(1, len(text) // 4)
