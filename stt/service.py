import io
import logging
from typing import Optional

from groq import AsyncGroq

from core.config import get_settings
from core.models import STTResult

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self):
        self._client = AsyncGroq(api_key=get_settings().groq_api_key)
        logger.info("STT: Groq whisper-large-v3-turbo")

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
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
