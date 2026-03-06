"""Single source of truth for all tuneable application settings.

All values read from environment variables with safe defaults.
Import from here rather than re-defining in individual modules.
"""

from __future__ import annotations

import os

# --- Message / session limits ---
MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "100"))
SESSION_TTL_MINUTES: int = int(os.getenv("SESSION_TTL_MINUTES", "90"))
STREAMING_TIMEOUT_SECONDS: int = int(os.getenv("STREAMING_TIMEOUT_SECONDS", "300"))

# --- Audio upload ---
MAX_AUDIO_SIZE_BYTES: int = int(os.getenv("MAX_AUDIO_SIZE_MB", "10")) * 1024 * 1024

# --- Rate limits (requests per window, read by slowapi decorators as strings) ---
RATE_LIMIT_MESSAGES_PER_HOUR: str = os.getenv("RATE_LIMIT_MESSAGES_PER_HOUR", "500")
RATE_LIMIT_SESSION_CREATION_PER_HOUR: str = os.getenv("RATE_LIMIT_SESSION_CREATION_PER_HOUR", "60")
RATE_LIMIT_VOICE_CONCURRENT: str = os.getenv("RATE_LIMIT_VOICE_CONCURRENT", "15")
RATE_LIMIT_HEALTHZ_PER_MINUTE: str = os.getenv("RATE_LIMIT_HEALTHZ_PER_MINUTE", "1000")

# --- Coach / RAG thresholds ---
LAYER_CONFIDENCE_THRESHOLD: float = 0.7
REFERENCE_MIN_SCORE: float = 0.68
REFERENCE_SCORE_MARGIN: float = 0.08
REFERENCE_POOL_SIZE: int = 5
EARLY_LESSON_MAX: int = 2
EARLY_LESSON_MARGIN: float = 0.08
