"""
tts/service.py — Silk mulberry TTS for Awaaz v2

Voice description = profile.mulberry_description (personality base)
                  + emotion suffix (per-call mood layer)

Speaker is always speaker_1 — best baseline for description-driven customization.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx

from core.config import settings
from core.user_profile import user_profile_store

logger = logging.getLogger(__name__)

SILK_BASE    = "https://silk-api.rumik.ai"
SILK_TTS_URL = f"{SILK_BASE}/v1/tts"

# Persistent client — avoids TLS handshake overhead on every TTS call (~400ms saved)
_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client




# Maps detected_mood → Mulberry description emotion word (from vd.md vocabulary)
# Mulberry understands: neutral, energetic, excited, sad, sarcastic, dry, crying, angry
MOOD_TO_MULBERRY_EMOTION: dict[str, str] = {
    "happy":        "energetic",
    "sad":          "sad",
    "excited":      "excited",
    "calm":         "neutral",
    "confident":    "energetic",
    "empathetic":   "neutral",
    "professional": "neutral",
    "sarcastic":    "sarcastic, dry",
    "angry":        "angry",
    "neutral":      "neutral",
    "whispering":   "neutral",
    "laughing":     "energetic",
    "shocked":      "excited",
    "scared":       "neutral",
}

DEFAULT_DESCRIPTION = "a warm 20s hindi accent voice, conversational pacing, casual register"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_description(detected_mood: str) -> str:
    """
    Profile base description (from onboarding) + Mulberry emotion word.
    Falls back to DEFAULT_DESCRIPTION if no profile exists.
    Text already contains Mulberry inline tags (<laugh>, <sigh>, etc.) —
    the description sets the overall character; tags handle specific moments.
    """
    profile     = user_profile_store.get()
    base        = profile.mulberry_description if profile else DEFAULT_DESCRIPTION
    emotion_mod = MOOD_TO_MULBERRY_EMOTION.get(detected_mood.lower(), "neutral")

    if emotion_mod and emotion_mod not in base:
        return f"{base}, {emotion_mod}"
    return base


# ─── Payload builder ─────────────────────────────────────────────────────────

def build_tts_payload(expressive_text: str, detected_mood: str = "neutral", f0_up_key: int = 0) -> dict:
    """
    Build the Mulberry API payload.
    expressive_text already contains <inline_tags> from the LLM — sent as-is.
    detected_mood drives the voice description's emotion word.
    """
    return {
        "model":       "mulberry",
        "text":        expressive_text,
        "description": _build_description(detected_mood),
        "f0_up_key":   f0_up_key,
    }


# ─── Core synthesis ───────────────────────────────────────────────────────────

async def synthesize(
    expressive_text: str,
    detected_mood: str = "neutral",
    save_path: Optional[Path] = None,
) -> bytes:
    """Call Silk mulberry and return raw WAV bytes (24 kHz mono)."""
    api_key = getattr(settings, "silk_api_key", None)
    if not api_key:
        raise RuntimeError("SILK_API_KEY is not set in .env")

    payload = build_tts_payload(expressive_text, detected_mood)

    logger.info(
        "TTS → mood=%s desc=%r text=%r",
        detected_mood,
        payload["description"][:80],
        payload["text"][:80],
    )

    client = _get_http_client()
    response = await client.post(
        SILK_TTS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        json=payload,
    )
    response.raise_for_status()

    wav_bytes = response.content
    logger.info("TTS ← %d bytes", len(wav_bytes))

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(wav_bytes)
        logger.debug("TTS saved → %s", save_path)

    return wav_bytes


async def synthesize_stream(
    expressive_text: str,
    detected_mood: str = "neutral",
) -> AsyncGenerator[bytes, None]:
    """Stream raw PCM chunks from Silk mulberry (WAV header stripped)."""
    api_key = getattr(settings, "silk_api_key", None)
    if not api_key:
        raise RuntimeError("SILK_API_KEY is not set in .env")

    payload = build_tts_payload(expressive_text, detected_mood)

    logger.info(
        "TTS stream → mood=%s desc=%r",
        detected_mood,
        payload["description"][:80],
    )

    client = _get_http_client()

    async with client.stream(
        "POST",
        SILK_TTS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    ) as response:
        response.raise_for_status()
        first = True
        async for chunk in response.aiter_bytes(chunk_size=4096):
            if first:
                chunk = chunk[44:] if len(chunk) >= 44 else b""
                first = False
            if chunk:
                yield chunk


# ─── /approve route helper ────────────────────────────────────────────────────

async def generate_tts_response(
    expressive_text: str,
    session_id: str,
    detected_mood: str = "neutral",
    output_dir: str = "tts_output",
) -> dict:
    """High-level helper for the /approve route."""
    output_path = Path(output_dir) / f"{session_id}.wav"
    wav_bytes = await synthesize(expressive_text, detected_mood, save_path=output_path)
    return {
        "tts_payload":     build_tts_payload(expressive_text, detected_mood),
        "tts_audio_url":   f"/{output_path}",
        "expressive_text": expressive_text,
        "audio_bytes":     wav_bytes,
    }


# ─── Smoke test — python -m tts.service ──────────────────────────────────────

if __name__ == "__main__":
    sample = "Hahaha yaar kya bol raha hai <laugh> seriously? <gasp> Wait what?!"
    payload = build_tts_payload(sample, detected_mood="laughing")

    print(f"Description : {payload['description']}")
    print(f"Text        : {payload['text']}")

    import asyncio

    async def _test():
        wav = await synthesize(sample, detected_mood="laughing", save_path=Path("test_output.wav"))
        print(f"✓ {len(wav):,} bytes → test_output.wav")

    asyncio.run(_test())
