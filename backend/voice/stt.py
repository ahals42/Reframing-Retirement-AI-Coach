"""Speech-to-text helper for voice chat."""

from __future__ import annotations

import io

from openai import OpenAI

DEFAULT_STT_MODEL = "whisper-1"


def transcribe_audio(
    client: OpenAI,
    audio_bytes: bytes,
    filename: str,
    *,
    model: str = DEFAULT_STT_MODEL,
) -> str:
    if not audio_bytes:
        return ""

    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = filename

    transcript = client.audio.transcriptions.create(
        model=model,
        file=file_obj,
        response_format="text",
    )

    if isinstance(transcript, str):
        return transcript.strip()
    if hasattr(transcript, "text"):
        return str(transcript.text).strip()
    return str(transcript).strip()
