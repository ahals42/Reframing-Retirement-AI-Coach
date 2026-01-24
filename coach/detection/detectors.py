"""Detection functions for user intent and emotional state."""

import re
from typing import Optional

from .text_match import _contains_patterns, _contains_keywords
from ..inference import (
    LOWEST_MPAC_STRONG_PATTERNS,
    LOWEST_MPAC_ACTIVITY_PATTERNS,
    GENERAL_DISINTEREST_PATTERNS,
    EMOTION_STRONG_PATTERNS,
    EMOTION_WEAK_PATTERNS,
    MODULE_REQUEST_PATTERNS,
    LESSON_LOOKUP_PATTERNS,
    EDUCATIONAL_REQUEST_PATTERNS,
    SOURCE_REQUEST_PATTERNS,
)
from ..constants import ACTIVITY_CONTEXT_KEYWORDS

# Import RouteDecision for type hint - use string annotation to avoid import at module level
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from rag.router import RouteDecision


def detect_lowest_mpac(text: str) -> bool:
    """Detect if user expresses lowest M-PAC (unmotivated/disengaged language)."""
    lowered = text.lower()
    if _contains_patterns(lowered, LOWEST_MPAC_STRONG_PATTERNS):
        return True
    if _contains_patterns(lowered, LOWEST_MPAC_ACTIVITY_PATTERNS):
        return True
    return False


def detect_general_disinterest(text: str) -> bool:
    """Detect if user expresses general disinterest in physical activity."""
    lowered = text.lower()
    if "?" in lowered:
        return False
    return _contains_patterns(lowered, GENERAL_DISINTEREST_PATTERNS)


def detect_emotion_regulation(text: str) -> bool:
    """Detect if user expresses negative emotions about physical activity."""
    lowered = text.lower()
    if _contains_patterns(lowered, EMOTION_STRONG_PATTERNS):
        return True
    if _contains_patterns(lowered, EMOTION_WEAK_PATTERNS) and _contains_keywords(lowered, ACTIVITY_CONTEXT_KEYWORDS):
        return True
    return False


def detect_module_request(text: str) -> bool:
    """Detect if user is asking about module/lesson content."""
    lowered = text.lower()
    return _contains_patterns(lowered, MODULE_REQUEST_PATTERNS)


def detect_lesson_lookup(text: str) -> bool:
    """Detect if user is asking which lesson covers a topic."""
    lowered = text.lower()
    return _contains_patterns(lowered, LESSON_LOOKUP_PATTERNS)


def detect_educational_use_case(text: str, *, explicit_module_request: bool, decision: Optional["RouteDecision"]) -> bool:
    """Detect if user is asking educational questions about physical activity."""
    if explicit_module_request:
        return True
    if decision and decision.use_activities:
        return False
    lowered = text.lower()
    return _contains_patterns(lowered, EDUCATIONAL_REQUEST_PATTERNS)


def detect_sources_only(text: str) -> bool:
    """Detect if user is only asking for sources/references."""
    lowered = text.lower()
    if not any(pattern.search(lowered) for pattern in SOURCE_REQUEST_PATTERNS):
        return False
    cleaned = lowered
    for pattern in SOURCE_REQUEST_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned).strip()
    return len(cleaned.split()) <= 2
