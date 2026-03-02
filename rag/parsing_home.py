"""Parsing utilities for the at-home resources dataset."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

SECTION_HEADER = re.compile(r"^=+\s*\n(.+?)\n=+", re.MULTILINE)
ENTRY_PATTERN = re.compile(
    r"Ref #:\s*(\d+)\s*\+{3}\s*Activity:\s*(.+?)(?=\n-{10,}|\Z)",
    re.DOTALL,
)

SECTION_RESOURCE_TYPE: Dict[str, str] = {
    "individual videos": "video",
    "video playlists": "playlist",
    "blogs": "blog",
}

TYPE_KEYWORDS: Dict[str, List[str]] = {
    "yoga": ["yoga"],
    "walking": ["walk", "walking"],
    "dance": ["dance"],
    "strength": ["strength", "resistance", "weights", "dumbbell", "pilates"],
    "aquatic": ["aqua", "swim", "water"],
    "chair": ["chair", "seated", "sitting"],
    "cardio": ["cardio", "aerobic", "hiit", "impact"],
    "stretch": ["stretch", "flexibility", "warm", "cool"],
    "balance": ["balance"],
}


def _infer_activity_type(name: str) -> str:
    lowered = name.lower()
    for label, keywords in TYPE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return label
    return "general"


@dataclass
class HomeActivityChunk:
    """Represents a single at-home resource record."""

    chunk_id: str
    text: str
    metadata: Dict[str, Any]


def parse_home_file(path: Path) -> List[HomeActivityChunk]:
    """Parse the at-home resources dataset into structured chunks."""

    if not path.exists():
        raise FileNotFoundError(f"At-home dataset not found at {path}")

    text = path.read_text(encoding="utf-8")
    chunks: List[HomeActivityChunk] = []

    # Split into sections by finding section headers
    sections = SECTION_HEADER.split(text)
    # sections is interleaved: [pre-text, header1, body1, header2, body2, ...]
    # index 0 is text before first header, then alternating header/body
    i = 1
    while i < len(sections):
        raw_header = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""
        i += 2

        # Determine resource type from section header
        resource_type = None
        for key, value in SECTION_RESOURCE_TYPE.items():
            if key in raw_header.lower():
                resource_type = value
                break
        if resource_type is None:
            continue

        # Parse entries within this section
        for match in ENTRY_PATTERN.finditer(body):
            ref_number = int(match.group(1))
            raw_title = match.group(2).strip()
            # Collapse multi-line titles (line continuations)
            activity_name = " ".join(raw_title.splitlines()).strip()

            chunk_id = f"home-{resource_type}-{ref_number:03d}"
            activity_type = _infer_activity_type(activity_name)

            metadata: Dict[str, Any] = {
                "doc_type": "home_activity",
                "chunk_id": chunk_id,
                "resource_type": resource_type,
                "ref_number": ref_number,
                "activity_name": activity_name,
                "activity_type": activity_type,
            }

            chunks.append(
                HomeActivityChunk(
                    chunk_id=chunk_id,
                    text=activity_name,
                    metadata=metadata,
                )
            )

    return chunks
