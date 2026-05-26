import io
import logging
from typing import Optional

import httpx

from core.config import get_settings
from core.models import STTResult

logger = logging.getLogger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


def is_valid_transcript(text: str) -> bool:
    words = text.strip().split()
    return len(words) >= 2 and len(text) > 10


class STTService:
    def __init__(self):
        self._api_key = get_settings().sarvam_api_key
        logger.info("STT: Sarvam Saaras v3 codemix")

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
    ) -> STTResult:
        client = _get_http_client()
        data: dict = {"model": "saaras:v3", "mode": "codemix"}
        if language:
            data["language_code"] = language
        response = await client.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": self._api_key},
            files={"file": (filename, io.BytesIO(audio_bytes), self._infer_mime(filename))},
            data=data,
        )
        response.raise_for_status()
        payload = response.json()
        transcript = payload.get("transcript", "").strip()

        if not is_valid_transcript(transcript):
            raise ValueError("Audio unclear or too short — please speak again.")

        return STTResult(
            transcript=transcript,
            detected_language=payload.get("language_code"),
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
