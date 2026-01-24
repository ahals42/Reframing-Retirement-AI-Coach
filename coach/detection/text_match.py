"""Text matching utilities for pattern and keyword detection."""

from typing import List, Pattern


def _contains_patterns(text: str, patterns: List[Pattern]) -> bool:
    """Check if text matches any of the compiled regex patterns."""
    return any(pattern.search(text) for pattern in patterns)


def _contains_keywords(text: str, keywords: List[str]) -> bool:
    """Check if text contains any of the keywords (case-insensitive)."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)
