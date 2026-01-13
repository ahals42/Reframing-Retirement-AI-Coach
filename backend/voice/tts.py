"""Text-to-speech helper for voice chat."""

from __future__ import annotations

from openai import OpenAI

DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_VOICE = "alloy"
DEFAULT_RESPONSE_FORMAT = "mp3"

_MIME_BY_FORMAT = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}


def synthesize_speech(
    client: OpenAI,
    text: str,
    *,
    model: str = DEFAULT_TTS_MODEL,
    voice: str = DEFAULT_VOICE,
    response_format: str = DEFAULT_RESPONSE_FORMAT,
) -> tuple[bytes, str]:
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format=response_format,
    )
    audio_bytes = response.content
    mime = _MIME_BY_FORMAT.get(response_format, "application/octet-stream")
    return audio_bytes, mime
