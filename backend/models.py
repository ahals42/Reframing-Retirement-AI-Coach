"""Pydantic schemas for the FastAPI backend."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    session_id: str = Field(..., description="Opaque session identifier.")


class MessageRequest(BaseModel):
    text: str = Field(..., description="User message text.")


class DeleteSessionResponse(BaseModel):
    message: str = Field(..., description="Confirmation message.")
