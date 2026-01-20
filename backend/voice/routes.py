"""FastAPI routes for voice chat (STT -> chat -> TTS) with security controls."""

from __future__ import annotations

import base64
import os
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, Request
from openai import OpenAI

from ..session_store import InMemorySessionStore
from ..middleware.auth import require_api_key
from ..middleware.rate_limit import limiter, RATE_LIMITS
from .stt import transcribe_audio
from .tts import synthesize_speech

logger = logging.getLogger(__name__)

# Security constants
MAX_AUDIO_SIZE_BYTES = int(os.getenv("MAX_AUDIO_SIZE_MB", "10")) * 1024 * 1024  # Default 10MB
ALLOWED_MIME_TYPES = ["audio/wav", "audio/webm", "audio/mpeg", "audio/mp4", "audio/ogg"]
ALLOWED_FILE_EXTENSIONS = [".wav", ".webm", ".mp3", ".m4a", ".ogg", ".opus"]


def create_voice_router(session_store: InMemorySessionStore, client: OpenAI) -> APIRouter:
    router = APIRouter()

    @router.post("/sessions/{session_id}/voice-chat")
    @require_api_key
    @limiter.limit(f"{RATE_LIMITS['messages_per_hour']}/hour")
    async def voice_chat(request: Request, session_id: str, audio: UploadFile = File(...)) -> dict:
        """
        Voice chat endpoint: transcribe audio, generate response, synthesize speech.

        Security features:
        - API key authentication required
        - Rate limiting per API key
        - File size validation
        - MIME type validation
        - Filename sanitization

        Args:
            request: FastAPI request (for auth/rate limiting)
            session_id: Session identifier
            audio: Audio file upload

        Returns:
            Dictionary with transcript, reply_text, and reply_audio (base64)
        """
        # Validate session exists
        record = session_store.get(session_id)
        if not record:
            logger.warning(f"Voice chat attempted for unknown session {session_id}")
            raise HTTPException(status_code=404, detail="Unknown session")

        # Read audio file
        audio_bytes = audio.file.read()

        # Validate audio size
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio payload")

        if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
            logger.warning(
                f"Audio file too large: {len(audio_bytes)} bytes "
                f"(max: {MAX_AUDIO_SIZE_BYTES} bytes) "
                f"from API key {request.state.api_key[:8]}..."
            )
            raise HTTPException(
                status_code=413,
                detail=f"Audio file too large. Maximum size: {MAX_AUDIO_SIZE_BYTES // (1024*1024)}MB"
            )

        # Validate and sanitize filename
        filename = audio.filename or "voice-input.webm"

        # Remove path traversal attempts
        filename = os.path.basename(filename)

        # Validate file extension
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_FILE_EXTENSIONS:
            logger.warning(
                f"Invalid file extension: {ext} "
                f"from API key {request.state.api_key[:8]}..."
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
            )

        # Validate MIME type if provided
        if audio.content_type and audio.content_type not in ALLOWED_MIME_TYPES:
            logger.warning(
                f"Invalid MIME type: {audio.content_type} "
                f"from API key {request.state.api_key[:8]}..."
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid MIME type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
            )

        logger.info(
            f"Voice chat request for session {session_id} "
            f"(audio size: {len(audio_bytes)} bytes, "
            f"filename: {filename}) "
            f"from API key {request.state.api_key[:8]}..."
        )

        # Transcribe audio using OpenAI Whisper
        try:
            transcript = transcribe_audio(client, audio_bytes, filename)
        except Exception as exc:
            logger.error(f"Failed to transcribe audio for session {session_id}: {exc}")
            raise HTTPException(status_code=500, detail="Unable to transcribe audio.") from exc

        transcript = transcript.strip()

        # Handle empty transcript
        if not transcript:
            logger.info(f"Empty transcript for session {session_id}")
            reply_text = "I did not catch that. Could you say it again?"
            reply_audio_bytes, reply_mime = synthesize_speech(client, reply_text)
            reply_audio = base64.b64encode(reply_audio_bytes).decode("ascii")
            return {
                "transcript": "",
                "reply_text": reply_text,
                "reply_audio": reply_audio,
                "reply_audio_mime": reply_mime,
            }

        # Generate coaching response
        try:
            reply_text = record.agent.generate_response(transcript)
        except Exception as exc:
            logger.error(f"Failed to generate response for session {session_id}: {exc}")
            raise HTTPException(status_code=500, detail="Unable to generate a reply.") from exc

        # Synthesize speech response
        try:
            reply_audio_bytes, reply_mime = synthesize_speech(client, reply_text)
        except Exception as exc:
            logger.error(f"Failed to synthesize speech for session {session_id}: {exc}")
            raise HTTPException(status_code=500, detail="Unable to synthesize speech.") from exc

        # Encode audio as base64 for JSON response
        reply_audio = base64.b64encode(reply_audio_bytes).decode("ascii")

        logger.info(
            f"Completed voice chat for session {session_id} "
            f"(transcript length: {len(transcript)}, "
            f"reply length: {len(reply_text)})"
        )

        return {
            "transcript": transcript,
            "reply_text": reply_text,
            "reply_audio": reply_audio,
            "reply_audio_mime": reply_mime,
        }

    return router
