"""
test_voice.py — Interactive voice enrollment + recognition + LLM test

Run from the awaaz/ root directory:
    python test_voice.py

Phase 1 — Enrollment:
    Records Voice 1 → asks name + relationship → saves
    Records Voice 2 → asks name + relationship → saves

Phase 2 — Recognition:
    Records a new clip → matches against saved voices
    → prints who was detected + similarity score
    → transcribes what was said
    → generates Hinglish expressive reply via LLM

Requirements:
    pip install sounddevice soundfile numpy
    (plus the main requirements.txt already installed)
"""

import asyncio
import sys
import io
import wave

import numpy as np
import sounddevice as sd
import soundfile as sf

from speaker.service import get_speaker_service
from stt.service import get_stt_service
from llm.service import get_llm_service
from core.models import Relationship

# ─── Audio config ────────────────────────────────────────────────────────────
SAMPLE_RATE  = 16000   # 16kHz — resemblyzer's native rate, no resampling needed
CHANNELS     = 1       # mono
RECORD_SECS  = 5       # seconds per clip — enough for resemblyzer to get a good embedding
DTYPE        = "int16"

RELATIONSHIP_CHOICES = [r.value for r in Relationship]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def print_divider(label: str = ""):
    width = 60
    if label:
        pad = (width - len(label) - 2) // 2
        print("\n" + "─" * pad + f" {label} " + "─" * pad)
    else:
        print("\n" + "─" * width)


def record_audio(prompt: str) -> bytes:
    """Record RECORD_SECS of audio from mic, return as WAV bytes."""
    print(f"\n🎙  {prompt}")
    input("    Press ENTER to start recording...")
    print(f"    Recording for {RECORD_SECS}s... speak now!")

    recording = sd.rec(
        int(RECORD_SECS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
    )
    sd.wait()
    print("    ✓ Done recording.")

    # Convert numpy array → WAV bytes in memory
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)           # int16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(recording.tobytes())
    return buf.getvalue()


def ask_relationship() -> Relationship:
    """Prompt user to pick a relationship from the enum."""
    print("\n    Relationship options:")
    for i, r in enumerate(RELATIONSHIP_CHOICES, 1):
        print(f"      {i}. {r}")
    while True:
        choice = input("    Enter number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(RELATIONSHIP_CHOICES):
            return Relationship(RELATIONSHIP_CHOICES[int(choice) - 1])
        print("    Invalid choice, try again.")


# ─── Phase 1: Enrollment ─────────────────────────────────────────────────────

async def enroll_voices(speaker_svc, n: int = 2):
    print_divider("PHASE 1 — VOICE ENROLLMENT")
    print(f"  We'll record {n} different voices and save them.")

    for i in range(1, n + 1):
        print_divider(f"Voice {i} of {n}")
        audio_bytes = record_audio(f"Say something as Voice {i} (5 seconds)")

        name = input("\n    Enter this person's name: ").strip() or f"Speaker{i}"
        relationship = ask_relationship()

        print(f"\n    Saving '{name}' ({relationship.value})...")
        profile = await speaker_svc.save_speaker(name, audio_bytes, relationship)
        print(f"    ✓ Saved! speaker_id: {profile.speaker_id[:8]}...")

    print_divider()
    print(f"  ✓ Enrolled {n} voices successfully.")


# ─── Phase 2: Recognition + STT + LLM ────────────────────────────────────────

async def recognize_and_reply(speaker_svc, stt_svc, llm_svc, clip_num: int):
    print_divider(f"RECOGNITION CLIP {clip_num}")
    audio_bytes = record_audio("Say something (5 seconds) — we'll identify you")

    # Run speaker ID and STT concurrently
    print("\n  Identifying speaker + transcribing...")
    speaker_result, stt_result = await asyncio.gather(
        speaker_svc.identify(audio_bytes),
        stt_svc.transcribe(audio_bytes, filename="audio.wav"),
    )

    # ── Speaker result ──
    print_divider("Speaker Detection")
    if speaker_result.is_new_speaker:
        print(f"  ❓ Unknown speaker  (best similarity: {speaker_result.similarity:.3f})")
        print("     (Below threshold — not matched to any saved voice)")
        # Fall back to asking relationship for LLM context
        print("\n  Since speaker is unknown, please provide relationship for LLM:")
        relationship = ask_relationship()
    else:
        print(f"  ✅ Identified : {speaker_result.name}")
        print(f"     Relationship: {speaker_result.relationship.value}")
        print(f"     Similarity  : {speaker_result.similarity:.4f}")
        relationship = speaker_result.relationship

    # ── STT result ──
    print_divider("Transcription")
    print(f"  Language  : {stt_result.detected_language or 'unknown'}")
    print(f"  Transcript: \"{stt_result.transcript}\"")

    if not stt_result.transcript.strip():
        print("\n  ⚠  Empty transcript — skipping LLM generation.")
        return

    # ── LLM generation ──
    print_divider("LLM — Expressive Hinglish Reply")
    print("  Generating reply...")
    llm_result = await llm_svc.generate(
        transcript=stt_result.transcript,
        relationship=relationship,
    )
    print(f"\n  Detected mood : {llm_result.detected_mood}")
    print(f"  Reasoning     : {llm_result.reasoning}")
    print(f"\n  Expressive text:")
    print(f"  ➤  {llm_result.expressive_text}")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "═" * 60)
    print("  AWAAZ v2 — Voice Test Script")
    print("═" * 60)

    speaker_svc = get_speaker_service()
    stt_svc     = get_stt_service()
    llm_svc     = get_llm_service()

    # ── Phase 1: enroll 2 voices ──
    await enroll_voices(speaker_svc, n=2)

    # ── Phase 2: recognition rounds ──
    print_divider("PHASE 2 — RECOGNITION + REPLY")
    print("  Now we'll record clips and see if the voices are matched.")
    print("  You can play both voices in any order — or someone new.")

    clip_num = 1
    while True:
        await recognize_and_reply(speaker_svc, stt_svc, llm_svc, clip_num)
        clip_num += 1
        print_divider()
        again = input("  Record another clip? (y/n): ").strip().lower()
        if again != "y":
            break

    print_divider()
    print("  Test complete. Voice profiles saved to voice_store/speakers.json")
    print("  They'll persist across runs — no need to re-enroll next time.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Exiting.")
        sys.exit(0)
        