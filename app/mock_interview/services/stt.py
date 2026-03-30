"""
mock_interview/services/stt.py
Speech-to-Text service using OpenAI Whisper.
OpenAI API key is read from the shared app Settings — never hardcoded.
"""

import io
from openai import AsyncOpenAI
from app.config import settings  # type: ignore

# Whisper hallucination filter
_HALLUCINATIONS = [
    "thank you.",
    "thank you",
    "thanks for watching.",
    "thanks for watching!",
    "subscribe",
    "please subscribe",
    "thank you for watching.",
    "subtitle by",
    "subtitles by",
    "captioned by",
]


async def speech_to_text(audio_bytes: bytes) -> str:
    """
    Transcribe raw WebM binary audio (from browser MediaRecorder) to text
    using OpenAI Whisper.
    """
    if not audio_bytes:
        return ""

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # MediaRecorder sends WebM blobs — tell the API filename so it knows the format
    file_tuple = ("audio.webm", audio_bytes, "audio/webm")

    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=file_tuple,
        temperature=0.0,
        language="en",
    )

    text = response.text.strip()

    # Filter silence hallucinations
    cleansed = text.lower()
    if any(h.lower() in cleansed for h in _HALLUCINATIONS) or len(text) < 3:
        return ""

    return text
