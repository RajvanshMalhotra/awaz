import io
import logging
from typing import Optional

from core.config import get_settings
from core.models import STTResult

logger = logging.getLogger(__name__)


class STTService:
    """
    Speech-to-text using Sarvam AI Saarika v2.5.

    Saarika v2.5 is trained specifically on Indian languages and Hinglish
    code-switching. language_code="unknown" enables auto-detection across
    all supported Indian languages + English.

    Falls back to Groq Whisper if SARVAM_API_KEY is not set.
    """

    def __init__(self):
        settings = get_settings()
        self._use_sarvam = bool(settings.sarvam_api_key)

        if self._use_sarvam:
            from sarvamai import AsyncSarvamAI
            self._client = AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)
            logger.info("STT: using Sarvam Saarika v2.5")
        else:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=settings.groq_api_key)
            logger.info("STT: SARVAM_API_KEY not set — falling back to Groq Whisper Turbo")

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
    ) -> STTResult:
        if self._use_sarvam:
            return await self._transcribe_sarvam(audio_bytes, filename)
        return await self._transcribe_groq(audio_bytes, filename, language)

    async def _transcribe_sarvam(self, audio_bytes: bytes, filename: str) -> STTResult:
        audio_file = (filename, io.BytesIO(audio_bytes), self._infer_mime(filename))
        response = await self._client.speech_to_text.transcribe(
            file=audio_file,
            model="saarika:v2.5",
            language_code="unknown",   # auto-detect; works for Hinglish
        )
        return STTResult(
            transcript=response.transcript.strip(),
            detected_language=response.language_code,
        )

    async def _transcribe_groq(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str],
    ) -> STTResult:
        audio_file = (filename, io.BytesIO(audio_bytes), self._infer_mime(filename))
        kwargs: dict = {
            "file": audio_file,
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
        }
        if language:
            kwargs["language"] = language
        response = await self._client.audio.transcriptions.create(**kwargs)
        return STTResult(
            transcript=response.text.strip(),
            detected_language=getattr(response, "language", None),
        )

    @staticmethod
    def _infer_mime(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower()
        return {
            "webm": "audio/webm",
            "wav":  "audio/wav",
            "mp3":  "audio/mpeg",
            "m4a":  "audio/mp4",
            "ogg":  "audio/ogg",
            "flac": "audio/flac",
        }.get(ext, "audio/webm")


_stt_service: Optional[STTService] = None


def get_stt_service() -> STTService:
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService()
    return _stt_service
