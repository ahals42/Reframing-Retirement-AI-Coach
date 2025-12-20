"""Parsing utilities for the activities dataset."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

CHUNK_DIVIDER = re.compile(r"\n\*{5,}\s*\n", flags=re.MULTILINE)
HEADER_PATTERN = re.compile(r"(?P<id>\d+)\.\s*(?P<name>[^\n]+)")
DAY_PATTERN = re.compile(
    r"\b(Mondays?|Tuesdays?|Wednesdays?|Thursdays?|Fridays?|Saturdays?|Sundays?|Weekends?|Daily)\b",
    flags=re.IGNORECASE,
)

TYPE_KEYWORDS = {
    "yoga": ["yoga"],
    "walking": ["walk", "walking"],
    "pickleball": ["pickleball"],
    "dance": ["dance", "zumba"],
    "strength": ["strength", "resistance", "weights", "pilates"],
    "aquatic": ["aqua", "swim", "water"],
    "kayaking": ["kayak"],
    "chair": ["chair"],
    "mind-body": ["tai chi", "soqi", "somatic", "mobility"],
}


@dataclass
class ActivityChunk:
    """Represents a single local activity record."""

    chunk_id: str
    text: str
    metadata: Dict[str, Any]


def _split_chunks(text: str) -> Iterable[str]:
    for piece in CHUNK_DIVIDER.split(text):
        cleaned = piece.strip()
        if cleaned:
            yield cleaned


def _extract_field(lines: List[str], label: str) -> str:
    prefix = f"{label.lower()}:"
    for line in lines:
        lowered = line.lower().strip()
        if lowered.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def _infer_cost_label(cost: str) -> str:
    lowered = cost.lower()
    if not lowered:
        return "unknown"
    if "free" in lowered or "no cost" in lowered:
        return "free"
    if any(char.isdigit() for char in cost) or "$" in cost:
        return "paid"
    return "unknown"


def _extract_cost_value(cost: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)", cost.replace(",", ""))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _normalize_days(when_text: str) -> List[str]:
    days: List[str] = []
    for match in DAY_PATTERN.finditer(when_text):
        value = match.group(1).lower()
        if value.startswith("mon"):
            normalized = "Monday"
        elif value.startswith("tue"):
            normalized = "Tuesday"
        elif value.startswith("wed"):
            normalized = "Wednesday"
        elif value.startswith("thu"):
            normalized = "Thursday"
        elif value.startswith("fri"):
            normalized = "Friday"
        elif value.startswith("sat"):
            normalized = "Saturday"
        elif value.startswith("sun"):
            normalized = "Sunday"
        elif value.startswith("weekend"):
            normalized = "Weekend"
        else:
            normalized = "Daily"
        days.append(normalized)
    # preserve order but remove duplicates
    seen = set()
    unique_days = []
    for day in days:
        if day not in seen:
            seen.add(day)
            unique_days.append(day)
    return unique_days


def _infer_activity_type(name: str, description: str) -> str:
    combined = f"{name} {description}".lower()
    for label, keywords in TYPE_KEYWORDS.items():
        if any(keyword in combined for keyword in keywords):
            return label
    return "general"


def _location_aliases(location: str) -> List[str]:
    lowered = location.lower()
    aliases: List[str] = []
    if "pear kes" in lowered or "gr pearkes" in lowered or "g.r. pearkes" in lowered:
        aliases.extend(["saanich", "g. r. pearkes", "pearkes"])
    if "silver threads" in lowered:
        aliases.extend(["silver threads", "fernwood", "downtown", "fairfield"])
    if "crystal pool" in lowered:
        aliases.extend(["crystal pool", "fernwood", "downtown"])
    if "cedar hill" in lowered:
        aliases.append("cedar hill")
    if "online" in lowered:
        aliases.extend(["online", "virtual", "home"])
    if "oak bay" in lowered or "uplands" in lowered:
        aliases.extend(["oak bay", "uplands", "oak bay recreation centre"])
    return aliases


def parse_activity_file(path: Path) -> List[ActivityChunk]:
    """Parse the activities dataset into structured chunks."""

    if not path.exists():
        raise FileNotFoundError(f"Activity dataset not found at {path}")

    text = path.read_text(encoding="utf-8")
    chunks: List[ActivityChunk] = []

    for segment in _split_chunks(text):
        header_match = HEADER_PATTERN.search(segment)
        if not header_match:
            continue

        activity_id = int(header_match.group("id"))
        name = header_match.group("name").strip()

        lines = [line.strip() for line in segment.splitlines() if line.strip()]
        what = _extract_field(lines, "What")
        where = _extract_field(lines, "Where")
        when_text = _extract_field(lines, "When")
        cost = _extract_field(lines, "Cost")

        cost_label = _infer_cost_label(cost)
        cost_value = _extract_cost_value(cost)
        days = _normalize_days(when_text)
        activity_type = _infer_activity_type(name, what)

        chunk_id = f"activity-{activity_id:03d}"
        combined_text = "\n".join(
            part for part in [name, what, where, when_text, cost] if part
        ).strip()

        metadata: Dict[str, Any] = {
            "doc_type": "activity",
            "chunk_id": chunk_id,
            "activity_id": activity_id,
            "activity_name": name,
            "description": what,
            "location": where,
            "schedule": when_text,
            "days": days,
            "cost_raw": cost,
            "cost_label": cost_label,
            "cost_value": cost_value,
            "activity_type": activity_type,
            "aliases": _location_aliases(where),
        }

        chunks.append(ActivityChunk(chunk_id=chunk_id, text=combined_text, metadata=metadata))

    return chunks
