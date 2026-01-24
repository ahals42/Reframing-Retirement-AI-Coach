"""Coach package exposing the conversational agent."""

"initializes OpenAI client, state, history"

from .agent import CoachAgent
from .state import ConversationState, LayerSignals, LayerInference
from .constants import (
    LAYER_CONFIDENCE_THRESHOLD,
    FREQUENCY_QUESTION,
    ROUTINE_QUESTION,
    TIMEFRAME_QUESTION,
)
from .inference import (
    infer_process_layer,
    pick_layer_question,
    infer_barrier,
    infer_activities,
    infer_time_available,
)
from .diagnostics import run_rag_sanity_check

__all__ = [
    "CoachAgent",
    "ConversationState",
    "LayerSignals",
    "LayerInference",
    "LAYER_CONFIDENCE_THRESHOLD",
    "FREQUENCY_QUESTION",
    "ROUTINE_QUESTION",
    "TIMEFRAME_QUESTION",
    "infer_process_layer",
    "pick_layer_question",
    "infer_barrier",
    "infer_activities",
    "infer_time_available",
    "run_rag_sanity_check",
]
