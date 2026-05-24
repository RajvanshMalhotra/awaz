"""
End-to-end API pipeline test for Awaaz v2.

Runs the real FastAPI routes in-process:
1. POST /onboarding
2. GET /onboarding/status
3. POST /pipeline/process  -> STT + speaker ID + Groq Llama
4. POST /pipeline/approve  -> Silk TTS

Run from repo root:
    python test_pipeline.py

Optional:
    python test_pipeline.py --audio voice_store/audio/example.wav
    python test_pipeline.py --keep-test-profile
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

import httpx

from main import app


DEFAULT_PERSONALITY = {
    "energy": "chaotic",
    "filter": "unfiltered",
    "style": "dramatic",
    "tone": "sarcastic",
    "lang_lean": "hindi",
}

DEFAULT_ONBOARDING = {
    "name": "Pipeline Tester",
    "voice_gender": "male",
    "personality": DEFAULT_PERSONALITY,
    "custom_vibe": "fast, funny, expressive Hinglish friend energy",
}

PROFILE_PATH = Path("user_profile.json")


def divider(label: str = "") -> None:
    width = 72
    if label:
        pad = max((width - len(label) - 2) // 2, 0)
        print("\n" + "-" * pad + f" {label} " + "-" * pad)
    else:
        print("\n" + "-" * width)


def find_default_audio() -> Path:
    candidates = sorted(Path("voice_store/audio").glob("*"))
    for path in candidates:
        if path.suffix.lower() in {".wav", ".mp3", ".m4a", ".webm", ".ogg"}:
            return path
    raise FileNotFoundError(
        "No audio file found under voice_store/audio. Pass one with --audio."
    )


def assert_ok(response: httpx.Response, label: str) -> dict[str, Any]:
    if response.status_code >= 400:
        print(f"\n{label} failed with HTTP {response.status_code}")
        print(response.text)
        raise SystemExit(1)
    try:
        return response.json()
    except ValueError:
        print(f"\n{label} returned non-JSON:")
        print(response.text[:1000])
        raise SystemExit(1)


def snapshot_profile() -> bytes | None:
    return PROFILE_PATH.read_bytes() if PROFILE_PATH.exists() else None


def restore_profile(snapshot: bytes | None) -> None:
    if snapshot is None:
        PROFILE_PATH.unlink(missing_ok=True)
    else:
        PROFILE_PATH.write_bytes(snapshot)


async def run_test(audio_path: Path, keep_test_profile: bool) -> None:
    profile_snapshot = snapshot_profile()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=120.0,
    ) as client:
        try:
            divider("Health")
            health = assert_ok(await client.get("/health"), "GET /health")
            print(f"status: {health['status']}")

            divider("Onboarding")
            onboarding = assert_ok(
                await client.post("/onboarding", json=DEFAULT_ONBOARDING),
                "POST /onboarding",
            )
            print(f"name: {onboarding['name']}")
            print(f"voice_gender: {onboarding['voice_gender']}")
            print(f"silk_speaker: {onboarding['silk_speaker']}")
            print(f"personality: {onboarding['personality']}")
            assert onboarding["personality"] == DEFAULT_PERSONALITY
            assert "llm_system_prompt" in onboarding
            assert "mulberry_description" in onboarding

            status = assert_ok(
                await client.get("/onboarding/status"),
                "GET /onboarding/status",
            )
            assert status["completed"] is True
            assert status["profile"]["personality"] == DEFAULT_PERSONALITY
            print("onboarding status: completed")

            divider("Process Audio")
            audio_bytes = audio_path.read_bytes()
            files = {
                "audio": (
                    audio_path.name,
                    audio_bytes,
                    "audio/wav" if audio_path.suffix.lower() == ".wav" else "application/octet-stream",
                )
            }
            data = {
                "relationship": "friend",
                "mood_override": "auto",
                "extra_text": "Keep it natural and personality-matched.",
                "voice_gender": DEFAULT_ONBOARDING["voice_gender"],
            }
            process = assert_ok(
                await client.post("/pipeline/process", data=data, files=files),
                "POST /pipeline/process",
            )
            print(f"transcript: {process['transcript']!r}")
            print(f"language: {process.get('detected_language')}")
            print(f"speaker new?: {process['speaker']['is_new_speaker']}")
            print(f"relationship: {process['effective_relationship']}")
            print(f"session_id: {process['session_id']}")
            print(f"llm mood: {process['llm']['detected_mood']}")
            print(f"llm text: {process['llm']['expressive_text']}")
            assert process["session_id"]
            assert process["transcript"].strip()
            assert process["llm"]["expressive_text"].strip()

            divider("Approve + TTS")
            approve = assert_ok(
                await client.post(
                    "/pipeline/approve",
                    json={"session_id": process["session_id"]},
                ),
                "POST /pipeline/approve",
            )
            print(f"tts_audio_url: {approve['tts_audio_url']}")
            print(f"tts speaker: {approve['tts_payload'].get('speaker')}")
            print(f"tts text: {approve['tts_payload'].get('text')}")
            assert approve["tts_payload"]["speaker"] == "speaker_3"
            assert approve["expressive_text"].strip()
            if approve["tts_audio_url"]:
                tts_path = Path(approve["tts_audio_url"])
                assert tts_path.exists(), f"TTS file not found: {tts_path}"
                assert tts_path.stat().st_size > 0, f"TTS file is empty: {tts_path}"
                print(f"tts bytes saved: {tts_path.stat().st_size:,}")

            divider()
            print("E2E pipeline test passed.")

        finally:
            if not keep_test_profile:
                restore_profile(profile_snapshot)
                print("Restored previous user_profile.json state.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full Awaaz onboarding -> STT -> LLM -> TTS test.")
    parser.add_argument(
        "--audio",
        type=Path,
        default=None,
        help="Audio file to send to /pipeline/process. Defaults to first voice_store/audio file.",
    )
    parser.add_argument(
        "--keep-test-profile",
        action="store_true",
        help="Keep the test onboarding profile instead of restoring the previous profile file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audio_path = args.audio or find_default_audio()
    if not audio_path.exists():
        print(f"Audio file does not exist: {audio_path}")
        sys.exit(1)

    print(f"Using audio: {audio_path}")
    asyncio.run(run_test(audio_path, args.keep_test_profile))


if __name__ == "__main__":
    main()
