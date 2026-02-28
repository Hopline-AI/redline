"""PDF parsing and section-aware text chunking."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber


def parse_pdf(path: str | Path) -> str:
    """Extract plain text from a PDF file using pdfplumber."""
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


# Patterns that indicate a new section heading
_SECTION_PATTERNS = [
    re.compile(r"^(?:SECTION|ARTICLE|CHAPTER|PART)\s+\d+", re.IGNORECASE),
    re.compile(r"^\d+\.\s+[A-Z]"),
    re.compile(r"^[IVXLC]+\.\s+"),
    re.compile(r"^[A-Z][A-Z\s]{4,}$"),
]


def _is_section_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(p.match(stripped) for p in _SECTION_PATTERNS)


def chunk_by_sections(text: str, max_chunk_chars: int = 3000) -> list[str]:
    """Split text into chunks, respecting section boundaries.

    Tries to split on section headings first. If a section exceeds
    max_chunk_chars, splits on paragraph boundaries within that section.
    """
    lines = text.split("\n")
    sections: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if _is_section_heading(line) and current:
            sections.append(current)
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append(current)

    chunks: list[str] = []
    for section_lines in sections:
        section_text = "\n".join(section_lines).strip()
        if not section_text:
            continue

        if len(section_text) <= max_chunk_chars:
            chunks.append(section_text)
        else:
            # Split long sections on paragraph boundaries
            paragraphs = re.split(r"\n\s*\n", section_text)
            current_chunk = ""
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if current_chunk and len(current_chunk) + len(para) + 2 > max_chunk_chars:
                    chunks.append(current_chunk)
                    current_chunk = para
                else:
                    current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            if current_chunk:
                chunks.append(current_chunk)

    return chunks
