"""Parsing utilities for the master slides dataset."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

CHUNK_DIVIDER = re.compile(r"\n\*{5,}\s*\n", flags=re.MULTILINE)
LESSON_PATTERN = re.compile(r"LESSON\s+(?P<num>\d+):\s*(?P<title>[^\n]+)", flags=re.IGNORECASE)
SLIDE_PATTERN = re.compile(r"L(?P<lesson>\d+)-S(?P<slide>\d+)-G(?P<global>\d+)", flags=re.IGNORECASE)
TITLE_PATTERN = re.compile(r"^Title:\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE)
CONTENT_PATTERN = re.compile(r"Content:\s*(.+)", flags=re.IGNORECASE | re.DOTALL)


@dataclass
class MasterChunk:
    """Represents a single slide chunk along with structured metadata."""

    chunk_id: str
    text: str
    metadata: Dict[str, Any]


def _clean_lesson_title(raw_title: str) -> str:
    title = raw_title.strip()
    title = re.sub(r"\(\d+[^)]*\)$", "", title).strip()
    return title


def _extract_slide_title(chunk: str) -> str:
    match = TITLE_PATTERN.search(chunk)
    if match:
        return match.group(1).strip()
    # fallback for lesson description slides
    desc_match = re.search(r"Lesson Description:\s*(.+)", chunk, flags=re.IGNORECASE)
    if desc_match:
        return desc_match.group(1).strip()
    return ""


def _extract_content(chunk: str) -> str:
    match = CONTENT_PATTERN.search(chunk)
    if match:
        return match.group(1).strip()
    # no explicit content block, return chunk minus markers
    cleaned = re.sub(r"\+\+\+\s*", "", chunk)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def _split_chunks(text: str) -> Iterable[str]:
    for piece in CHUNK_DIVIDER.split(text):
        cleaned = piece.strip()
        if cleaned:
            yield cleaned


def parse_master_file(path: Path) -> List[MasterChunk]:
    """Parse the master dataset into structured chunks."""

    if not path.exists():
        raise FileNotFoundError(f"Master dataset not found at {path}")

    text = path.read_text(encoding="utf-8")
    lesson_titles: Dict[int, str] = {}

    chunks: List[MasterChunk] = []
    for segment in _split_chunks(text):
        lesson_match = LESSON_PATTERN.search(segment)
        if lesson_match:
            lesson_number = int(lesson_match.group("num"))
            lesson_titles[lesson_number] = _clean_lesson_title(lesson_match.group("title"))

        slide_match = SLIDE_PATTERN.search(segment)
        if not slide_match:
            continue

        lesson_number = int(slide_match.group("lesson"))
        slide_number = int(slide_match.group("slide"))
        global_slide_number = int(slide_match.group("global"))
        lesson_title = lesson_titles.get(lesson_number, "")

        slide_title = _extract_slide_title(segment)
        content = _extract_content(segment)
        merged_text = "\n".join(
            part for part in [f"Lesson {lesson_number}", f"Slide {slide_number}", slide_title, content] if part
        ).strip()

        lower_title = slide_title.lower()
        do_not_reference_marker = "***DO NOT REFERENCE***" in segment.upper()
        references_title = any(keyword in lower_title for keyword in ["reference", "references", "bibliography", "citations"])
        do_not_reference = do_not_reference_marker or references_title
        chunk_id = f"master-L{lesson_number:02d}-S{slide_number:02d}-G{global_slide_number:03d}"

        metadata: Dict[str, Any] = {
            "doc_type": "master",
            "chunk_id": chunk_id,
            "lesson_number": lesson_number,
            "slide_number": slide_number,
            "global_slide_number": global_slide_number,
            "lesson_title": lesson_title,
            "slide_title": slide_title,
            "do_not_reference": do_not_reference,
        }

        chunks.append(MasterChunk(chunk_id=chunk_id, text=merged_text, metadata=metadata))

    return chunks
