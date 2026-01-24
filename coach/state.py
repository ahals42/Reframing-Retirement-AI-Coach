"""Dataclasses for conversation state and layer inference."""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass
class LayerSignals:
    """Stores detected cues that hint at reflective/regulatory/reflexive focus."""

    has_frequency: bool = False
    has_timeframe: bool = False
    has_routine_language: bool = False
    has_planning_language: bool = False
    has_not_started_language: bool = False
    has_affective_language: bool = False
    has_opportunity_language: bool = False
    has_progressive_statement: bool = False

    @property
    def behavior_evidence(self) -> bool:
        return (
            self.has_frequency
            or self.has_timeframe
            or self.has_routine_language
            or self.has_progressive_statement
        )


@dataclass
class LayerInference:
    """Represents the inferred process layer and supporting metadata."""

    layer: str | None
    confidence: float
    signals: LayerSignals


@dataclass
class ConversationState:
    """Tracks inferred user context for prompt conditioning."""

    process_layer: str = "unclassified"
    layer_confidence: float = 0.0
    pending_layer_question: str | None = None
    barrier: str = "unknown"
    activities: str = "unknown"
    time_available: str = "unknown"

    def to_prompt_mapping(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class _PreparedPrompt:
    """Internal dataclass for prepared prompt data."""

    messages: List[Dict[str, str]]
    needs_citations: bool
    override_citations: bool
    override_text: str
    reference_block_references: List[str]
    response_mode: str
    module_reference_sentence: str
