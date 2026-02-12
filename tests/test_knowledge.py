"""Tests for knowledge loading."""
import json
import tempfile
from pathlib import Path

from src.knowledge.loader import Chunk, load_knowledge


def test_load_json_faq(tmp_path: Path):
    """Test loading FAQ from JSON."""
    faq = [
        {"q": "What is X?", "a": "X is a thing.", "tags": ["test"]},
        {"q": "How does Y work?", "a": "Y works like this."},
    ]
    faq_file = tmp_path / "faq.json"
    faq_file.write_text(json.dumps(faq))

    chunks = load_knowledge(str(tmp_path))
    assert len(chunks) == 2
    assert chunks[0].source == "faq.json"
    assert "What is X?" in chunks[0].text
    assert chunks[0].heading == "What is X?"


def test_load_markdown(tmp_path: Path):
    """Test loading and chunking markdown."""
    md_content = """# Title

Introduction paragraph.

## Section One

Content of section one. This is a paragraph with some details.

## Section Two

Content of section two.
"""
    md_file = tmp_path / "guide.md"
    md_file.write_text(md_content)

    chunks = load_knowledge(str(tmp_path))
    assert len(chunks) >= 2
    assert any("Section One" in c.heading for c in chunks)


def test_load_text(tmp_path: Path):
    """Test loading plain text."""
    txt = "First paragraph about topic A.\n\nSecond paragraph about topic B."
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text(txt)

    chunks = load_knowledge(str(tmp_path))
    assert len(chunks) >= 1
    assert chunks[0].source == "notes.txt"


def test_empty_directory(tmp_path: Path):
    """Test loading from empty directory."""
    chunks = load_knowledge(str(tmp_path))
    assert chunks == []


def test_missing_directory():
    """Test loading from non-existent directory."""
    chunks = load_knowledge("/nonexistent/path")
    assert chunks == []
