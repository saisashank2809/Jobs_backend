"""
mock_interview/services/tts.py
Text-to-Speech service using OpenAI TTS.
Streams PCM 16-bit, 24kHz, mono audio chunks suitable for Web Audio API playback.
OpenAI API key is read from the shared app Settings — never hardcoded.
"""

from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings  # type: ignore


async def text_to_speech_stream(text: str) -> AsyncGenerator[bytes, None]:
    """
    Convert text to speech using OpenAI TTS-1 and yield raw PCM audio chunks.
    Output: PCM 16-bit, 24kHz, mono — matches what the frontend WebAudio Api expects.
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    async with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="alloy",
        input=text,
        response_format="pcm",
    ) as response:
        async for chunk in response.iter_bytes(chunk_size=4096):
            if chunk:
                yield chunk
