import io
import asyncio
from typing import Optional

from groq import AsyncGroq

from core.config import get_settings
from core.models import STTResult


class STTService:
    """
    Speech-to-text using Groq's Whisper Large v3.

    Flow:
    1. Audio bytes → in-memory file-like object
    2. POST to Groq transcriptions endpoint
    3. Returns transcript + detected language

    Groq runs Whisper on their infra — typical latency ~300–600ms for short clips.
    Multilingual: Whisper v3 auto-detects language; pass `language` hint to speed
    up inference if known.

    Free tier: ~28hr audio/day — well within hackathon demo limits.
    """

    def __init__(self):
        settings = get_settings()
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = "whisper-large-v3"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
    ) -> STTResult:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio (webm, wav, mp3, m4a — Groq accepts all).
            filename:    Hint for MIME type detection; default webm for browser recordings.
            language:    ISO-639-1 code (e.g. 'en', 'hi'). None = auto-detect.

        Returns:
            STTResult with transcript and detected_language.
        """
        audio_file = (filename, io.BytesIO(audio_bytes), self._infer_mime(filename))

        kwargs: dict = {
            "file": audio_file,
            "model": self._model,
            "response_format": "verbose_json",  # gives us language detection
        }
        if language:
            kwargs["language"] = language

        response = await self._client.audio.transcriptions.create(**kwargs)

        return STTResult(
            transcript=response.text.strip(),
            detected_language=getattr(response, "language", None),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_mime(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower()
        mime_map = {
            "webm": "audio/webm",
            "wav":  "audio/wav",
            "mp3":  "audio/mpeg",
            "m4a":  "audio/mp4",
            "ogg":  "audio/ogg",
            "flac": "audio/flac",
        }
        return mime_map.get(ext, "audio/webm")


# Singleton
_stt_service: Optional[STTService] = None


def get_stt_service() -> STTService:
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService()
    return _stt_service