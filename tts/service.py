# """
# tts/service.py — Silk (rumik.ai) mulberry TTS for Awaaz v2

# Model: silk mulberry 1.5
#   - Steered by a natural-language description built from the detected emotion
#   - Voice (gender) selected via speaker_1..speaker_4, set during onboarding
#     and stored in user profile / passed in at call time
#   - f0_up_key allows fine pitch tuning per user preference

# Speaker presets (from Silk docs — try them in the playground):
#     speaker_1  female  (default)
#     speaker_2  female  (slightly different timbre)
#     speaker_3  male
#     speaker_4  male    (deeper)

# LLM output format:
#     (laughing)Hahaha...Thatsofunny... (shocked)Wait...Ohmygod...

# Pipeline:
#   1. Parse dominant emotion from first (emotion) block
#   2. Strip all (emotion) markers → clean spoken text
#   3. Build a natural-language description from the emotion
#   4. POST to /v1/tts with speaker chosen at onboarding
#   5. Return 24 kHz mono WAV bytes

# Environment variables (.env):
#     SILK_API_KEY=rk_live_...
#     SILK_DEFAULT_SPEAKER=speaker_1       # overridden per user at runtime
#     SILK_DEFAULT_F0_UP_KEY=0             # semitone pitch shift, -12..12
# """

# from __future__ import annotations

# import re
# import asyncio
# import logging
# from pathlib import Path
# from typing import Literal, Optional

# import httpx

# from core.config import settings

# logger = logging.getLogger(__name__)

# # ---------------------------------------------------------------------------
# # Silk API
# # ---------------------------------------------------------------------------
# SILK_BASE    = "https://silk-api.rumik.ai"
# SILK_TTS_URL = f"{SILK_BASE}/v1/tts"

# SilkSpeaker = Literal["speaker_1", "speaker_2", "speaker_3", "speaker_4"]

# # Convenience aliases so the onboarding UI can use plain strings
# GENDER_TO_SPEAKER: dict[str, SilkSpeaker] = {
#     "female":        "speaker_1",
#     "female_alt":    "speaker_2",
#     "male":          "speaker_3",
#     "male_deep":     "speaker_4",
# }

# # ---------------------------------------------------------------------------
# # Emotion → mulberry description
# # mulberry is steered by free-text description, so we write a short phrase
# # that captures the Awaaz emotion in a way the model understands.
# # ---------------------------------------------------------------------------
# EMOTION_TO_DESCRIPTION: dict[str, str] = {
#     "laughing":   "laughing, light-hearted, highly amused",
#     "shocked":    "shocked and surprised, slightly breathless",
#     "whispering": "whispering softly, hushed and intimate",
#     "sad":        "sad, slow and subdued",
#     "angry":      "frustrated and irritated, sharp delivery",
#     "scared":     "nervous and anxious, slightly trembling voice",
#     "sarcastic":  "deadpan and dry, mildly sarcastic",
#     "happy":      "cheerful, warm, and upbeat",
#     "neutral":    "clear, calm, and conversational",
#     "excited":    "excited and energetic, fast-paced",
# }

# DEFAULT_DESCRIPTION = "expressive, conversational Hinglish speaker"

# _EMOTION_BLOCK_RE = re.compile(
#     r"\((?P<emotion>[a-z]+)\)(?P<text>[^(]+)",
#     re.IGNORECASE,
# )

# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def _parse_emotion_and_text(expressive_text: str) -> tuple[str, str]:
#     """
#     Returns (dominant_emotion, clean_text).

#     dominant_emotion — the first (emotion) tag found, lowercased
#     clean_text       — expressive_text with all (emotion) markers stripped
#     """
#     blocks = _EMOTION_BLOCK_RE.findall(expressive_text)

#     if not blocks:
#         return "neutral", expressive_text.strip()

#     dominant_emotion = blocks[0][0].lower()
#     clean_text = _EMOTION_BLOCK_RE.sub(lambda m: m.group("text"), expressive_text).strip()
#     return dominant_emotion, clean_text


# def build_tts_payload(
#     expressive_text: str,
#     speaker: SilkSpeaker = "speaker_1",
#     f0_up_key: int = 0,
# ) -> dict:
#     """
#     Build the JSON body for POST /v1/tts (mulberry).

#     Args:
#         expressive_text: LLM output — "(laughing)Haha yaar... (excited)Sach mein?!"
#         speaker:         Silk preset voice; chosen during onboarding
#                          speaker_1/2 → female  |  speaker_3/4 → male
#         f0_up_key:       Pitch shift in semitones (-12..+12); user preference
#     """
#     emotion, clean_text = _parse_emotion_and_text(expressive_text)
#     description = EMOTION_TO_DESCRIPTION.get(emotion, DEFAULT_DESCRIPTION)

#     return {
#         "model":       "mulberry",
#         "text":        clean_text,
#         "description": description,
#         "speaker":     speaker,
#         "f0_up_key":   f0_up_key,
#     }


# def resolve_speaker(
#     speaker: Optional[SilkSpeaker] = None,
#     gender: Optional[str] = None,
# ) -> SilkSpeaker:
#     """
#     Resolve to a concrete Silk speaker preset.

#     Priority:
#       1. Explicit speaker string passed in (from user profile)
#       2. gender string mapped via GENDER_TO_SPEAKER
#       3. SILK_DEFAULT_SPEAKER env var
#       4. "speaker_1" hard fallback
#     """
#     if speaker and speaker in ("speaker_1", "speaker_2", "speaker_3", "speaker_4"):
#         return speaker
#     if gender and gender in GENDER_TO_SPEAKER:
#         return GENDER_TO_SPEAKER[gender]
#     default = getattr(settings, "silk_default_speaker", "speaker_1")
#     return default if default in ("speaker_1", "speaker_2", "speaker_3", "speaker_4") else "speaker_1"


# # ---------------------------------------------------------------------------
# # Core async synthesis
# # ---------------------------------------------------------------------------

# async def synthesize(
#     expressive_text: str,
#     speaker: Optional[SilkSpeaker] = None,
#     gender: Optional[str] = None,
#     f0_up_key: Optional[int] = None,
#     save_path: Optional[Path] = None,
# ) -> bytes:
#     """
#     Call Silk mulberry and return raw WAV bytes (24 kHz mono).

#     Args:
#         expressive_text: LLM output in (emotion)Text... format
#         speaker:         Silk speaker preset (from onboarding profile)
#         gender:          "female" | "female_alt" | "male" | "male_deep"
#                          used if speaker is not given
#         f0_up_key:       Pitch shift; falls back to SILK_DEFAULT_F0_UP_KEY or 0
#         save_path:       If given, write WAV here too

#     Returns:
#         Raw WAV bytes

#     Raises:
#         RuntimeError if SILK_API_KEY is missing
#         httpx.HTTPStatusError on non-2xx API response
#     """
#     api_key = getattr(settings, "silk_api_key", None)
#     if not api_key:
#         raise RuntimeError(
#             "SILK_API_KEY is not set. Add SILK_API_KEY=rk_live_... to your .env"
#         )

#     resolved_speaker = resolve_speaker(speaker=speaker, gender=gender)
#     resolved_f0      = f0_up_key if f0_up_key is not None else int(
#         getattr(settings, "silk_default_f0_up_key", 0)
#     )

#     payload = build_tts_payload(expressive_text, speaker=resolved_speaker, f0_up_key=resolved_f0)

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type":  "application/json",
#     }

#     logger.info(
#         "TTS → speaker=%s f0=%+d emotion=%s text_preview=%r",
#         resolved_speaker,
#         resolved_f0,
#         _parse_emotion_and_text(expressive_text)[0],
#         payload["text"][:80],
#     )

#     async with httpx.AsyncClient(timeout=30.0) as client:
#         response = await client.post(SILK_TTS_URL, headers=headers, json=payload)
#         response.raise_for_status()

#     wav_bytes = response.content
#     logger.info("TTS ← %d bytes received", len(wav_bytes))

#     if save_path:
#         save_path = Path(save_path)
#         save_path.parent.mkdir(parents=True, exist_ok=True)
#         save_path.write_bytes(wav_bytes)
#         logger.info("TTS saved → %s", save_path)

#     return wav_bytes


# # ---------------------------------------------------------------------------
# # /approve route helper — called from api/pipeline.py
# # ---------------------------------------------------------------------------

# async def generate_tts_response(
#     expressive_text: str,
#     session_id: str,
#     speaker: Optional[SilkSpeaker] = None,
#     gender: Optional[str] = None,
#     f0_up_key: Optional[int] = None,
#     output_dir: str = "tts_output",
# ) -> dict:
#     """
#     High-level helper for the /approve route.

#     Pass speaker (or gender) from the user's onboarding profile.

#     Returns:
#     {
#         "tts_payload":     dict   — exact JSON sent to Silk (for debugging)
#         "tts_audio_url":   str    — local WAV path (serve via /static or swap for CDN URL)
#         "expressive_text": str    — original LLM text
#         "audio_bytes":     bytes  — raw WAV (stream directly if preferred)
#     }
#     """
#     output_path = Path(output_dir) / f"{session_id}.wav"

#     wav_bytes = await synthesize(
#         expressive_text,
#         speaker=speaker,
#         gender=gender,
#         f0_up_key=f0_up_key,
#         save_path=output_path,
#     )

#     resolved_speaker = resolve_speaker(speaker=speaker, gender=gender)
#     resolved_f0      = f0_up_key if f0_up_key is not None else int(
#         getattr(settings, "silk_default_f0_up_key", 0)
#     )

#     return {
#         "tts_payload":     build_tts_payload(expressive_text, speaker=resolved_speaker, f0_up_key=resolved_f0),
#         "tts_audio_url":   str(output_path),
#         "expressive_text": expressive_text,
#         "audio_bytes":     wav_bytes,
#     }


# # ---------------------------------------------------------------------------
# # Smoke test — python -m tts.service
# # ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     sample = "(laughing)Hahaha yaar kya bol raha hai tu... (shocked)Wait seriously?! (excited)Sach mein bata!"

#     emotion, clean = _parse_emotion_and_text(sample)
#     print(f"Dominant emotion : {emotion}")
#     print(f"Clean text       : {clean}")
#     print(f"Description      : {EMOTION_TO_DESCRIPTION.get(emotion)}")
#     print()

#     for gender, spk in GENDER_TO_SPEAKER.items():
#         payload = build_tts_payload(sample, speaker=spk)
#         print(f"[{gender:12s} → {spk}]  payload={payload}")

#     print()

#     async def _test():
#         # Will fail without a real SILK_API_KEY — but payload printing above works
#         wav = await synthesize(
#             sample,
#             gender="female",          # onboarding choice
#             save_path=Path("test_tts_output.wav"),
#         )
#         print(f"✓ Got {len(wav):,} bytes → test_tts_output.wav")

#     asyncio.run(_test())

"""
tts/service.py — Silk mulberry TTS for Awaaz v2

Mulberry voice description is sourced from the user profile when available.
Speaker (gender) also comes from the profile — no need to pass it per-call
unless you want to override.
"""

from __future__ import annotations

import re
import asyncio
import logging
from pathlib import Path
from typing import Literal, Optional

import httpx

from core.config import settings
from core.user_profile import user_profile_store, GENDER_TO_SPEAKER

logger = logging.getLogger(__name__)

SILK_BASE    = "https://silk-api.rumik.ai"
SILK_TTS_URL = f"{SILK_BASE}/v1/tts"

SilkSpeaker = Literal["speaker_1", "speaker_2", "speaker_3", "speaker_4"]

# ─── Emotion → mulberry description suffix ────────────────────────────────────
# Applied ON TOP of the user's base voice description.
# e.g. "male voice, chill, punchy, dry..." + ", laughing and highly amused"

EMOTION_DESCRIPTION_SUFFIX: dict[str, str] = {
    "laughing":   ", laughing and highly amused",
    "shocked":    ", shocked and surprised, slightly breathless",
    "whispering": ", whispering softly, hushed",
    "sad":        ", sad and subdued",
    "angry":      ", frustrated and sharp",
    "scared":     ", nervous and anxious",
    "sarcastic":  ", deadpan and dry",
    "happy":      ", cheerful and warm",
    "neutral":    "",
    "excited":    ", excited and energetic",
}

DEFAULT_DESCRIPTION = "expressive conversational Hinglish speaker"

_EMOTION_BLOCK_RE = re.compile(r"\((?P<emotion>[a-z]+)\)(?P<text>[^(]+)", re.IGNORECASE)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_emotion_and_text(expressive_text: str) -> tuple[str, str]:
    blocks = _EMOTION_BLOCK_RE.findall(expressive_text)
    if not blocks:
        return "neutral", expressive_text.strip()
    dominant = blocks[0][0].lower()
    clean    = _EMOTION_BLOCK_RE.sub(lambda m: m.group("text"), expressive_text).strip()
    return dominant, clean


def _resolve_description(emotion: str) -> str:
    """
    Build final mulberry description:
      profile base description  +  emotion suffix
    Falls back to DEFAULT_DESCRIPTION if no profile.
    """
    profile = user_profile_store.get()
    base    = profile.mulberry_description if profile else DEFAULT_DESCRIPTION
    suffix  = EMOTION_DESCRIPTION_SUFFIX.get(emotion, "")
    return base + suffix


def _resolve_speaker(
    speaker: Optional[SilkSpeaker] = None,
    gender:  Optional[str] = None,
) -> SilkSpeaker:
    """Priority: explicit arg → profile voice_gender → env default → speaker_1"""
    if speaker in ("speaker_1", "speaker_2", "speaker_3", "speaker_4"):
        return speaker
    if gender and gender in GENDER_TO_SPEAKER:
        return GENDER_TO_SPEAKER[gender]
    profile = user_profile_store.get()
    if profile:
        return profile.silk_speaker()
    default = getattr(settings, "silk_default_speaker", "speaker_1")
    return default if default in ("speaker_1", "speaker_2", "speaker_3", "speaker_4") else "speaker_1"


def build_tts_payload(
    expressive_text: str,
    speaker: Optional[SilkSpeaker] = None,
    gender:  Optional[str] = None,
    f0_up_key: int = 0,
) -> dict:
    emotion, clean_text = _parse_emotion_and_text(expressive_text)
    description         = _resolve_description(emotion)
    resolved_speaker    = _resolve_speaker(speaker=speaker, gender=gender)

    return {
        "model":       "mulberry",
        "text":        clean_text,
        "description": description,
        "speaker":     resolved_speaker,
        "f0_up_key":   f0_up_key,
    }


# ─── Core synthesis ───────────────────────────────────────────────────────────

async def synthesize(
    expressive_text: str,
    speaker:   Optional[SilkSpeaker] = None,
    gender:    Optional[str] = None,
    f0_up_key: Optional[int] = None,
    save_path: Optional[Path] = None,
) -> bytes:
    api_key = getattr(settings, "silk_api_key", None)
    if not api_key:
        raise RuntimeError("SILK_API_KEY is not set in .env")

    resolved_f0 = f0_up_key if f0_up_key is not None else int(
        getattr(settings, "silk_default_f0_up_key", 0)
    )

    payload = build_tts_payload(expressive_text, speaker=speaker, gender=gender, f0_up_key=resolved_f0)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    emotion = _parse_emotion_and_text(expressive_text)[0]
    logger.info(
        "TTS → speaker=%s emotion=%s desc=%r text_preview=%r",
        payload["speaker"], emotion, payload["description"][:60], payload["text"][:60],
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(SILK_TTS_URL, headers=headers, json=payload)
        response.raise_for_status()

    wav_bytes = response.content
    logger.info("TTS ← %d bytes", len(wav_bytes))

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(wav_bytes)

    return wav_bytes


# ─── /approve route helper ────────────────────────────────────────────────────

async def generate_tts_response(
    expressive_text: str,
    session_id: str,
    speaker:   Optional[SilkSpeaker] = None,
    gender:    Optional[str] = None,
    f0_up_key: Optional[int] = None,
    output_dir: str = "tts_output",
) -> dict:
    output_path = Path(output_dir) / f"{session_id}.wav"

    wav_bytes = await synthesize(
        expressive_text,
        speaker=speaker,
        gender=gender,
        f0_up_key=f0_up_key,
        save_path=output_path,
    )

    resolved_speaker = _resolve_speaker(speaker=speaker, gender=gender)
    resolved_f0      = f0_up_key if f0_up_key is not None else int(
        getattr(settings, "silk_default_f0_up_key", 0)
    )

    return {
        "tts_payload":     build_tts_payload(expressive_text, speaker=resolved_speaker, f0_up_key=resolved_f0),
        "tts_audio_url":   str(output_path),
        "expressive_text": expressive_text,
        "audio_bytes":     wav_bytes,
    }


# ─── Smoke test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample = "(laughing)Hahaha yaar kya bol raha hai... (shocked)Wait seriously?!"
    emotion, clean = _parse_emotion_and_text(sample)
    payload = build_tts_payload(sample)
    print(f"Emotion     : {emotion}")
    print(f"Clean text  : {clean}")
    print(f"Description : {payload['description']}")
    print(f"Speaker     : {payload['speaker']}")
    print(f"Payload     : {payload}")