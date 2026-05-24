"""
test_tts_only.py — Isolated TTS test (no STT, no LLM, no mic)

Run from awaaz/ root:
    python test_tts_only.py

Tests Silk mulberry directly with a hardcoded expressive Hinglish string.
Saves output to tts_output/tts_test.wav and plays it back.
"""

import asyncio
import io
import sys
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from tts.service import generate_tts_response, build_tts_payload, EMOTION_TO_DESCRIPTION

VOICE_GENDER_OPTIONS = ["female", "female_alt", "male", "male_deep"]

# A few test strings to try — covers different emotions
TEST_SAMPLES = [
    ("laughing",   "(laughing)Hahaha yaar kya bol raha hai tu... (excited)Sach mein bata!"),
    ("shocked",    "(shocked)Wait wait wait...Ohmygod...Areyouserious yaar?!"),
    ("sad",        "(sad)Yaar...bahut bura laga...sach mein nahi chahiye tha aisa..."),
    ("angry",      "(angry)Arre bhai...kya kar raha hai tu...bilkul bakwaas hai yeh..."),
    ("sarcastic",  "(sarcastic)Haan haan...bahut acha kiya...bilkul perfect..."),
]


def divider(label=""):
    w = 60
    if label:
        pad = (w - len(label) - 2) // 2
        print("\n" + "─" * pad + f" {label} " + "─" * pad)
    else:
        print("\n" + "─" * w)


def play_wav(wav_bytes: bytes):
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        rate     = wf.getframerate()
        channels = wf.getnchannels()
        frames   = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels)
    print("    🔊 Playing...")
    sd.play(audio, samplerate=rate)
    sd.wait()
    print("    ✓ Done.")


def pick(options, label):
    print(f"\n  {label}:")
    for i, o in enumerate(options, 1):
        print(f"    {i}. {o}")
    while True:
        raw = input("  Enter number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  Invalid — try again.")


async def main():
    print("\n" + "═" * 60)
    print("  AWAAZ v2 — TTS Isolated Test")
    print("═" * 60)

    # Pick voice
    divider("Voice")
    gender = pick(VOICE_GENDER_OPTIONS, "Pick voice gender")
    print(f"  ✓ {gender}")

    # Pick or enter text
    divider("Input Text")
    print("  Options:")
    print("    0. Type your own expressive text")
    for i, (emotion, text) in enumerate(TEST_SAMPLES, 1):
        print(f"    {i}. [{emotion}] {text[:60]}...")

    while True:
        raw = input("\n  Enter number (0 for custom): ").strip()
        if raw == "0":
            expressive_text = input("  Enter text (use (emotion)Text format): ").strip()
            break
        if raw.isdigit() and 1 <= int(raw) <= len(TEST_SAMPLES):
            expressive_text = TEST_SAMPLES[int(raw) - 1][1]
            break
        print("  Invalid — try again.")

    print(f"\n  Input  : {expressive_text}")

    # Show what will be sent to Silk
    payload = build_tts_payload(expressive_text, speaker="speaker_3" if "male" in gender else "speaker_1")
    divider("Silk Payload")
    print(f"  model      : {payload['model']}")
    print(f"  speaker    : {payload['speaker']}")
    print(f"  description: {payload['description']}")
    print(f"  text       : {payload['text']}")

    # Call TTS
    divider("Synthesizing")
    Path("tts_output").mkdir(exist_ok=True)
    print(f"  Calling Silk mulberry API...")

    try:
        result = await generate_tts_response(
            expressive_text=expressive_text,
            session_id="tts_test",
            gender=gender,
            output_dir="tts_output",
        )
        print(f"  ✓ {len(result['audio_bytes']):,} bytes received")
        print(f"  ✓ Saved → {result['tts_audio_url']}")

        divider("Playback")
        play_wav(result["audio_bytes"])

    except Exception as e:
        print(f"\n  ✗ TTS failed: {e}")
        sys.exit(1)

    divider()
    print("  TTS test passed.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(0)