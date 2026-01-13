"""FastAPI routes for voice chat (STT -> chat -> TTS)."""

from __future__ import annotations

import base64

from fastapi import APIRouter, File, HTTPException, UploadFile
from openai import OpenAI

from ..session_store import InMemorySessionStore
from .stt import transcribe_audio
from .tts import synthesize_speech


def create_voice_router(session_store: InMemorySessionStore, client: OpenAI) -> APIRouter:
    router = APIRouter()

    @router.post("/sessions/{session_id}/voice-chat")
    def voice_chat(session_id: str, audio: UploadFile = File(...)) -> dict:
        record = session_store.get(session_id)
        if not record:
            raise HTTPException(status_code=404, detail="Unknown session")

        audio_bytes = audio.file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio payload")

        filename = audio.filename or "voice-input.webm"

        try:
            transcript = transcribe_audio(client, audio_bytes, filename)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Unable to transcribe audio.") from exc

        transcript = transcript.strip()

        if not transcript:
            reply_text = "I did not catch that. Could you say it again?"
            reply_audio_bytes, reply_mime = synthesize_speech(client, reply_text)
            reply_audio = base64.b64encode(reply_audio_bytes).decode("ascii")
            return {
                "transcript": "",
                "reply_text": reply_text,
                "reply_audio": reply_audio,
                "reply_audio_mime": reply_mime,
            }

        try:
            reply_text = record.agent.generate_response(transcript)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Unable to generate a reply.") from exc

        try:
            reply_audio_bytes, reply_mime = synthesize_speech(client, reply_text)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Unable to synthesize speech.") from exc

        reply_audio = base64.b64encode(reply_audio_bytes).decode("ascii")
        return {
            "transcript": transcript,
            "reply_text": reply_text,
            "reply_audio": reply_audio,
            "reply_audio_mime": reply_mime,
        }

    return router
