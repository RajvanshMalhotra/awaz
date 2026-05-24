# """
# End-to-end API pipeline test for Awaaz v2.

# Runs the real FastAPI routes in-process:
# 1. POST /onboarding
# 2. GET /onboarding/status
# 3. POST /pipeline/process  -> STT + speaker ID + Groq Llama
# 4. POST /pipeline/approve  -> Silk TTS

# Run from repo root:
#     python test_pipeline.py

# Optional:
#     python test_pipeline.py --audio voice_store/audio/example.wav
#     python test_pipeline.py --keep-test-profile
# """

# from __future__ import annotations

# import argparse
# import asyncio
# import sys
# from pathlib import Path
# from typing import Any

# import httpx

# from main import app


# DEFAULT_PERSONALITY = {
#     "energy": "chaotic",
#     "filter": "unfiltered",
#     "style": "dramatic",
#     "tone": "sarcastic",
#     "lang_lean": "hindi",
# }

# DEFAULT_ONBOARDING = {
#     "name": "Pipeline Tester",
#     "voice_gender": "male",
#     "personality": DEFAULT_PERSONALITY,
#     "custom_vibe": "fast, funny, expressive Hinglish friend energy",
# }

# PROFILE_PATH = Path("user_profile.json")


# def divider(label: str = "") -> None:
#     width = 72
#     if label:
#         pad = max((width - len(label) - 2) // 2, 0)
#         print("\n" + "-" * pad + f" {label} " + "-" * pad)
#     else:
#         print("\n" + "-" * width)


# def find_default_audio() -> Path:
#     candidates = sorted(Path("voice_store/audio").glob("*"))
#     for path in candidates:
#         if path.suffix.lower() in {".wav", ".mp3", ".m4a", ".webm", ".ogg"}:
#             return path
#     raise FileNotFoundError(
#         "No audio file found under voice_store/audio. Pass one with --audio."
#     )


# def assert_ok(response: httpx.Response, label: str) -> dict[str, Any]:
#     if response.status_code >= 400:
#         print(f"\n{label} failed with HTTP {response.status_code}")
#         print(response.text)
#         raise SystemExit(1)
#     try:
#         return response.json()
#     except ValueError:
#         print(f"\n{label} returned non-JSON:")
#         print(response.text[:1000])
#         raise SystemExit(1)


# def snapshot_profile() -> bytes | None:
#     return PROFILE_PATH.read_bytes() if PROFILE_PATH.exists() else None


# def restore_profile(snapshot: bytes | None) -> None:
#     if snapshot is None:
#         PROFILE_PATH.unlink(missing_ok=True)
#     else:
#         PROFILE_PATH.write_bytes(snapshot)


# async def run_test(audio_path: Path, keep_test_profile: bool) -> None:
#     profile_snapshot = snapshot_profile()

#     transport = httpx.ASGITransport(app=app)
#     async with httpx.AsyncClient(
#         transport=transport,
#         base_url="http://testserver",
#         timeout=120.0,
#     ) as client:
#         try:
#             divider("Health")
#             health = assert_ok(await client.get("/health"), "GET /health")
#             print(f"status: {health['status']}")

#             divider("Onboarding")
#             onboarding = assert_ok(
#                 await client.post("/onboarding", json=DEFAULT_ONBOARDING),
#                 "POST /onboarding",
#             )
#             print(f"name: {onboarding['name']}")
#             print(f"voice_gender: {onboarding['voice_gender']}")
#             print(f"silk_speaker: {onboarding['silk_speaker']}")
#             print(f"personality: {onboarding['personality']}")
#             assert onboarding["personality"] == DEFAULT_PERSONALITY
#             assert "llm_system_prompt" in onboarding
#             assert "mulberry_description" in onboarding

#             status = assert_ok(
#                 await client.get("/onboarding/status"),
#                 "GET /onboarding/status",
#             )
#             assert status["completed"] is True
#             assert status["profile"]["personality"] == DEFAULT_PERSONALITY
#             print("onboarding status: completed")

#             divider("Process Audio")
#             audio_bytes = audio_path.read_bytes()
#             files = {
#                 "audio": (
#                     audio_path.name,
#                     audio_bytes,
#                     "audio/wav" if audio_path.suffix.lower() == ".wav" else "application/octet-stream",
#                 )
#             }
#             data = {
#                 "relationship": "friend",
#                 "mood_override": "auto",
#                 "extra_text": "Keep it natural and personality-matched.",
#                 "voice_gender": DEFAULT_ONBOARDING["voice_gender"],
#             }
#             process = assert_ok(
#                 await client.post("/pipeline/process", data=data, files=files),
#                 "POST /pipeline/process",
#             )
#             print(f"transcript: {process['transcript']!r}")
#             print(f"language: {process.get('detected_language')}")
#             print(f"speaker new?: {process['speaker']['is_new_speaker']}")
#             print(f"relationship: {process['effective_relationship']}")
#             print(f"session_id: {process['session_id']}")
#             print(f"llm mood: {process['llm']['detected_mood']}")
#             print(f"llm text: {process['llm']['expressive_text']}")
#             assert process["session_id"]
#             assert process["transcript"].strip()
#             assert process["llm"]["expressive_text"].strip()

#             divider("Approve + TTS")
#             approve = assert_ok(
#                 await client.post(
#                     "/pipeline/approve",
#                     json={"session_id": process["session_id"]},
#                 ),
#                 "POST /pipeline/approve",
#             )
#             print(f"tts_audio_url: {approve['tts_audio_url']}")
#             print(f"tts speaker: {approve['tts_payload'].get('speaker')}")
#             print(f"tts text: {approve['tts_payload'].get('text')}")
#             assert approve["tts_payload"]["speaker"] == "speaker_3"
#             assert approve["expressive_text"].strip()
#             if approve["tts_audio_url"]:
#                 tts_path = Path(approve["tts_audio_url"])
#                 assert tts_path.exists(), f"TTS file not found: {tts_path}"
#                 assert tts_path.stat().st_size > 0, f"TTS file is empty: {tts_path}"
#                 print(f"tts bytes saved: {tts_path.stat().st_size:,}")

#             divider()
#             print("E2E pipeline test passed.")

#         finally:
#             if not keep_test_profile:
#                 restore_profile(profile_snapshot)
#                 print("Restored previous user_profile.json state.")


# def parse_args() -> argparse.Namespace:
#     parser = argparse.ArgumentParser(description="Run full Awaaz onboarding -> STT -> LLM -> TTS test.")
#     parser.add_argument(
#         "--audio",
#         type=Path,
#         default=None,
#         help="Audio file to send to /pipeline/process. Defaults to first voice_store/audio file.",
#     )
#     parser.add_argument(
#         "--keep-test-profile",
#         action="store_true",
#         help="Keep the test onboarding profile instead of restoring the previous profile file.",
#     )
#     return parser.parse_args()


# def main() -> None:
#     args = parse_args()
#     audio_path = args.audio or find_default_audio()
#     if not audio_path.exists():
#         print(f"Audio file does not exist: {audio_path}")
#         sys.exit(1)

#     print(f"Using audio: {audio_path}")
#     asyncio.run(run_test(audio_path, args.keep_test_profile))


# if __name__ == "__main__":
#     main()

"""
test_full_pipeline.py — Complete Awaaz v2 End-to-End Test

Tests the full flow:
  1. Onboarding  — POST /onboarding (name, voice_gender, personality, custom_vibe)
  2. Status      — GET  /onboarding/status (verify profile persisted)
  3. Record      — capture mic audio via sounddevice
  4. STT         — Groq Whisper transcription (via STT service directly)
  5. LLM         — Groq Llama expressive Hinglish reply
  6. TTS         — Silk mulberry synthesis
  7. Playback    — hear the output
  8. Deny/Regen  — regenerate with a mood override
  9. Teardown    — DELETE /onboarding (optional cleanup)

Run from awaaz/ root:
    python test_full_pipeline.py

Requirements:
    pip install sounddevice numpy httpx
    .env with GROQ_API_KEY and SILK_API_KEY set
"""

import asyncio
import io
import json
import sys
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

# ── Import app services directly (no HTTP server needed) ─────────────────────
try:
    from core.config import get_settings
    from core.models import Mood, Relationship
    from core.user_profile import user_profile_store, Personality, GENDER_TO_SPEAKER
    from stt.service import get_stt_service
    from llm.service import get_llm_service
    from tts.service import generate_tts_response, build_tts_payload, EMOTION_DESCRIPTION_SUFFIX
    from core.session_store import session_store
    from onboarding_cli import run_onboarding as cli_run_onboarding
except ImportError as e:
    print(f"\n✗ Import failed: {e}")
    print("  Run from the awaaz/ project root: python test_full_pipeline.py")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR   = Path("tts_output")
SAMPLE_RATE  = 16_000      # Hz — Whisper optimal
RECORD_SECS  = 5           # default recording duration (user can override)
CHANNELS     = 1
DTYPE        = "int16"

VOICE_GENDERS = ["female", "female_alt", "male", "male_deep"]
RELATIONSHIPS = [r.value for r in Relationship]
MOODS         = [m.value for m in Mood]

ENERGY_OPTIONS   = ["chill", "chaotic"]
FILTER_OPTIONS   = ["clean", "unfiltered"]
STYLE_OPTIONS    = ["punchy", "dramatic"]
TONE_OPTIONS     = ["sincere", "sarcastic"]
LANG_OPTIONS     = ["hindi", "english"]

# ── Terminal helpers ──────────────────────────────────────────────────────────

W = 64

def banner(text=""):
    if text:
        pad = (W - len(text) - 2) // 2
        print("\n" + "─" * pad + f" {text} " + "─" * (W - pad - len(text) - 2))
    else:
        print("─" * W)

def ok(msg):   print(f"  ✓ {msg}")
def fail(msg): print(f"  ✗ {msg}")
def info(msg): print(f"  · {msg}")
def step(n, label): print(f"\n{'═'*W}\n  STEP {n}: {label}\n{'═'*W}")

def pick(options: list, label: str, default_idx: int = 0) -> str:
    print(f"\n  {label}:")
    for i, o in enumerate(options, 1):
        marker = " (default)" if i - 1 == default_idx else ""
        print(f"    {i}. {o}{marker}")
    while True:
        raw = input(f"  Enter number [default {default_idx+1}]: ").strip()
        if raw == "":
            return options[default_idx]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  Invalid — try again.")

def ask(prompt: str, default: str = "") -> str:
    raw = input(f"  {prompt}" + (f" [{default}]: " if default else ": ")).strip()
    return raw if raw else default

def yesno(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    raw = input(f"  {prompt}{suffix}").strip().lower()
    if raw == "":
        return default
    return raw in ("y", "yes")

# ── Audio helpers ─────────────────────────────────────────────────────────────

def record_audio(duration: int = RECORD_SECS) -> bytes:
    """Record mic audio and return raw WAV bytes."""
    print(f"\n  🎙  Recording for {duration}s — speak now...")
    frames = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
    )
    # Show a live countdown
    for remaining in range(duration, 0, -1):
        print(f"    {remaining}s remaining...", end="\r", flush=True)
        time.sleep(1)
    sd.wait()
    print("    Done recording.   ")

    # Convert numpy array → WAV bytes
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)          # int16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(frames.tobytes())
    return buf.getvalue()


def play_wav(wav_bytes: bytes):
    """Play WAV bytes through speakers."""
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        rate     = wf.getframerate()
        channels = wf.getnchannels()
        frames   = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels)
    print("  🔊 Playing back response...")
    sd.play(audio, samplerate=rate)
    sd.wait()
    ok("Playback complete.")

# ── Pipeline steps ────────────────────────────────────────────────────────────

def run_onboarding() -> dict:
    """Interactive onboarding — uses CLI onboarding flow from onboarding_cli.py."""
    step(1, "ONBOARDING")
    profile = cli_run_onboarding()
    
    # Reload LLM so it picks up the new profile
    get_llm_service().reload_profile()
    ok("LLM service reloaded with new profile.")

    return profile


def verify_onboarding_status():
    """Verify profile persisted correctly."""
    step(2, "VERIFY ONBOARDING STATUS")
    profile = user_profile_store.get()
    if profile is None:
        fail("Profile not found after save!")
        sys.exit(1)
    ok(f"Profile loaded: {profile.name} / {profile.voice_gender}")
    info(f"Personality: {profile.personality.to_dict()}")


async def run_stt(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Run STT on recorded audio, return transcript."""
    step(4, "SPEECH-TO-TEXT (Groq Whisper)")
    stt = get_stt_service()
    info("Sending audio to Groq Whisper Large v3...")
    t0 = time.time()
    result = await stt.transcribe(audio_bytes, filename=filename)
    elapsed = time.time() - t0
    ok(f"Transcript ({elapsed:.2f}s): \"{result.transcript}\"")
    if result.detected_language:
        info(f"Detected language: {result.detected_language}")
    if not result.transcript.strip():
        fail("Empty transcript — check mic / audio quality.")
        sys.exit(1)
    return result.transcript


async def run_llm(transcript: str, relationship: Relationship, mood_override: Mood) -> object:
    """Run LLM and return LLMResult."""
    step(5, "LLM — EXPRESSIVE HINGLISH GENERATION")
    llm = get_llm_service()
    info(f"Relationship : {relationship.value}")
    info(f"Mood override: {mood_override.value}")
    info("Sending to Groq Llama...")
    t0 = time.time()
    result = await llm.generate(
        transcript=transcript,
        relationship=relationship,
        mood_override=mood_override,
    )
    elapsed = time.time() - t0
    ok(f"Generated ({elapsed:.2f}s)")
    banner("LLM Output")
    print(f"  Detected mood  : {result.detected_mood}")
    print(f"  Reasoning      : {result.reasoning}")
    print(f"  Expressive text: {result.expressive_text}")
    return result


async def run_tts(llm_result, session_id: str = "test_session") -> dict:
    """Run TTS and return result dict with audio bytes."""
    step(6, "TTS — SILK MULBERRY SYNTHESIS")
    OUTPUT_DIR.mkdir(exist_ok=True)
    payload = build_tts_payload(llm_result.expressive_text)
    info(f"Speaker     : {payload['speaker']}")
    info(f"Description : {payload['description'][:70]}...")
    info(f"Clean text  : {payload['text'][:70]}...")
    info("Calling Silk mulberry API...")
    t0 = time.time()
    result = await generate_tts_response(
        expressive_text=llm_result.expressive_text,
        session_id=session_id,
        output_dir=str(OUTPUT_DIR),
    )
    elapsed = time.time() - t0
    ok(f"Synthesis done ({elapsed:.2f}s) — {len(result['audio_bytes']):,} bytes")
    ok(f"Saved → {result['tts_audio_url']}")
    return result


async def run_deny_regen(transcript: str, relationship: Relationship, original_result) -> object:
    """Simulate a deny → regenerate with a different mood."""
    step(7, "DENY / REGENERATE")
    print("\n  Simulating user tapping 'Deny' and picking a different mood.\n")
    new_mood = pick(MOODS, "Override mood for regen", default_idx=MOODS.index("excited"))
    llm = get_llm_service()
    info(f"Regenerating with mood: {new_mood}...")
    t0 = time.time()
    new_result = await llm.generate(
        transcript=transcript,
        relationship=relationship,
        mood_override=Mood(new_mood),
    )
    elapsed = time.time() - t0
    ok(f"Regenerated ({elapsed:.2f}s)")
    banner("Regenerated LLM Output")
    print(f"  Detected mood  : {new_result.detected_mood}")
    print(f"  Expressive text: {new_result.expressive_text}")
    return new_result


def teardown():
    """Optionally clear the onboarding profile."""
    step(9, "TEARDOWN (optional)")
    if yesno("Clear the saved profile?", default=False):
        user_profile_store.clear()
        ok("Profile cleared.")
    else:
        info("Profile kept.")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "═" * W)
    print("  AWAAZ v2 — Full Pipeline Test")
    print("  Onboarding → Record → STT → LLM → TTS → Playback")
    print("═" * W)

    # ── Validate settings ──
    settings = get_settings()
    banner("Environment Check")
    if not settings.groq_api_key:
        fail("GROQ_API_KEY missing from .env")
        sys.exit(1)
    ok(f"GROQ_API_KEY   : {'*' * 8}{settings.groq_api_key[-4:]}")
    if not settings.silk_api_key:
        fail("SILK_API_KEY missing from .env")
        sys.exit(1)
    ok(f"SILK_API_KEY   : {'*' * 8}{settings.silk_api_key[-4:]}")
    ok(f"Groq LLM model : {settings.groq_llm_model}")

    # STEP 1: Onboarding
    if yesno("\n  Run onboarding step? (skip if profile already saved)", default=True):
        run_onboarding()
    else:
        info("Skipping onboarding — using existing profile.")
        get_llm_service().reload_profile()

    # STEP 2: Verify
    verify_onboarding_status()

    # STEP 3: Record
    step(3, "RECORD AUDIO")
    dur_raw = ask("Recording duration in seconds", str(RECORD_SECS))
    try:
        duration = max(1, min(30, int(dur_raw)))
    except ValueError:
        duration = RECORD_SECS

    relationship = Relationship(pick(RELATIONSHIPS, "Relationship context for this message", default_idx=0))
    mood_override = Mood(pick(MOODS, "Mood override (use 'auto' to let LLM decide)", default_idx=0))

    audio_bytes = record_audio(duration=duration)
    ok(f"Captured {len(audio_bytes):,} bytes of audio")

    # STEP 4: STT
    transcript = await run_stt(audio_bytes)

    # STEP 5: LLM
    llm_result = await run_llm(transcript, relationship, mood_override)

    # STEP 6: TTS
    tts_result = await run_tts(llm_result, session_id="test_full_pipeline")

    # STEP 7: Playback
    step(7, "PLAYBACK")
    play_wav(tts_result["audio_bytes"])

    # STEP 8: Deny / Regen (optional)
    if yesno("\n  Test deny/regenerate flow?", default=True):
        new_llm = await run_deny_regen(transcript, relationship, llm_result)
        step(8, "TTS FOR REGENERATED REPLY")
        new_tts = await run_tts(new_llm, session_id="test_regen")
        play_wav(new_tts["audio_bytes"])

    # STEP 9: Teardown
    teardown()

    banner()
    print("\n  ✅ All pipeline steps completed successfully!\n")
    print(f"  Output WAV files saved in: {OUTPUT_DIR}/\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ✗ Pipeline failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)