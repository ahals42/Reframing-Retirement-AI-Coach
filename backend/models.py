"""Pydantic schemas for the FastAPI backend with input validation."""

from __future__ import annotations

import os
from pydantic import BaseModel, Field, field_validator


class SessionCreateResponse(BaseModel):
    session_id: str = Field(..., description="Opaque session identifier.")


class MessageRequest(BaseModel):
    """
    User message request with input validation.

    Security constraints:
    - Maximum message length to prevent memory exhaustion
    - Content sanitization for prompt injection prevention
    """
    text: str = Field(
        ...,
        description="User message text.",
        max_length=int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
    )

    @field_validator('text')
    @classmethod
    def validate_text_not_empty(cls, v: str) -> str:
        """Ensure message text is not empty or only whitespace."""
        if not v or not v.strip():
            raise ValueError("Message text cannot be empty")
        return v.strip()

    @field_validator('text')
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """
        Basic sanitization to detect obvious prompt injection attempts.

        This is a lightweight defense-in-depth measure.
        The agent layer has additional protections.
        """
        # Check for excessive repetition (potential DoS)
        if len(v) > 100:
            # Count repeated characters
            max_repeat = max(
                (v.count(c) for c in set(v) if c.isalnum()),
                default=0
            )
            if max_repeat > len(v) * 0.8:  # More than 80% same character
                raise ValueError("Message contains excessive repetition")

        return v


class DeleteSessionResponse(BaseModel):
    message: str = Field(..., description="Confirmation message.")
