"""
core/user_profile.py — User personality profiles for Awaaz v2

Multiple profiles are supported. One is "active" at a time.
get() always returns the active profile for backward compatibility.

Storage: user_profiles.json
  {
    "active_id": "uuid",
    "profiles": {
      "uuid": { "profile_id": "uuid", "name": "Raj", "personality": {...}, ... }
    }
  }

Migration: if user_profile.json exists (v1 single-profile), it is auto-imported
on first load as the initial profile.
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal, Optional

from core.config import settings

logger = logging.getLogger(__name__)

PROFILES_PATH = Path("user_profiles.json")
LEGACY_PATH   = Path(getattr(settings, "user_profile_path", "user_profile.json"))

# ─── Personality dimensions ───────────────────────────────────────────────────

Energy    = Literal["chill", "chaotic"]
Filter    = Literal["clean", "unfiltered"]
Style     = Literal["punchy", "dramatic"]
Tone      = Literal["sincere", "sarcastic"]
LangLean  = Literal["hindi", "english"]


@dataclass
class Personality:
    energy:    Energy
    filter:    Filter
    style:     Style
    tone:      Tone
    lang_lean: LangLean

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Personality":
        return cls(**d)


@dataclass
class UserProfile:
    profile_id:          str
    name:                str
    personality:         Personality
    custom_vibe:         str
    llm_system_prompt:   str
    mulberry_description: str

    def to_dict(self) -> dict:
        return {
            "profile_id":            self.profile_id,
            "name":                  self.name,
            "personality":           self.personality.to_dict(),
            "custom_vibe":           self.custom_vibe,
            "llm_system_prompt":     self.llm_system_prompt,
            "mulberry_description":  self.mulberry_description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        return cls(
            profile_id=d.get("profile_id", str(_uuid.uuid4())),
            name=d["name"],
            personality=Personality.from_dict(d["personality"]),
            custom_vibe=d.get("custom_vibe", ""),
            llm_system_prompt=d["llm_system_prompt"],
            mulberry_description=d["mulberry_description"],
        )


# ─── Prompt + description generation ─────────────────────────────────────────

EMOTION_TAGS = [
    "happy", "sad", "excited", "calm", "confident", "empathetic",
    "professional", "sarcastic", "angry", "neutral", "whispering",
    "laughing", "shocked", "scared",
]


def build_llm_system_prompt(name: str, p: Personality, custom_vibe: str = "") -> str:
    """
    Generates a personality-aware voice-generation system prompt.
    The LLM speaks ON BEHALF of the user — it generates what the user wants to say
    in their own voice and personality, with Mulberry inline tags for expressiveness.
    Built for the mute user community: they input intent, LLM outputs their voice.
    """
    energy_desc = (
        "high-energy, spontaneous, expressive — you speak with enthusiasm and intensity"
        if p.energy == "chaotic"
        else "calm, measured, relaxed — you speak at an easy, unhurried pace"
    )
    filter_desc = (
        "very direct and unfiltered — you say exactly what you mean, no sugarcoating"
        if p.filter == "unfiltered"
        else "thoughtful and measured — you choose words carefully"
    )
    style_desc = (
        "expressive and dramatic — you emphasise feelings and paint vivid pictures"
        if p.style == "dramatic"
        else "punchy and concise — you get to the point fast"
    )
    tone_desc = (
        "dry and sarcastic — you use wit and irony naturally"
        if p.tone == "sarcastic"
        else "warm and sincere — you speak with genuine feeling"
    )
    lang_desc = (
        "Hindi-dominant Hinglish — more Hindi words, English only when natural"
        if p.lang_lean == "hindi"
        else "English-dominant Hinglish — mostly English with Hindi expressions sprinkled in"
    )

    custom_vibe = custom_vibe.strip()
    vibe_section = f"\nAdditional voice character: {custom_vibe}" if custom_vibe else ""

    inline_tags = ", ".join([
        "<laugh>", "<laugh_harder>", "<chuckle>", "<giggle>", "<snort>",
        "<sigh>", "<exhale>", "<gasp>", "<gulp>",
        "<excited>", "<angry>", "<whisper>", "<cry>", "<scream>",
        "<sarcastic>", "<curious>",
    ])

    return f"""You are the voice of {name}. {name} is unable to speak and uses this app to communicate.

YOUR JOB: When {name} gives you what they want to say, generate a natural spoken response in their exact voice — how they would actually say it, with their personality, emotion, and Hinglish style. Then insert Mulberry inline tags to make the TTS delivery expressive.

{name.upper()}'S PERSONALITY:
- Energy: {energy_desc}
- Filter: {filter_desc}
- Style: {style_desc}
- Tone: {tone_desc}
- Language: {lang_desc}{vibe_section}

RULES:
1. Keep the core meaning and intent of what {name} wants to say — do not change the topic or add unrelated content
2. Rephrase into natural spoken Hinglish that sounds like {name} — conversational, not written
3. Keep it concise: 1–3 sentences maximum
4. Insert 1–3 Mulberry inline tags at moments where a natural sound/expression fits
5. Always reply in Roman script (no Devanagari) — TTS requires it
6. If mood_override is set, match that emotional tone in both the words and the tags

Available inline tags: {inline_tags}

Tag placement: put the tag at the exact moment of expression — "seriously? <gasp> yaar that's wild"

OUTPUT — valid JSON only, no markdown:
{{
  "expressive_text": "<{name}'s natural spoken response with <inline_tags> inserted>",
  "detected_mood": "<primary emotion: happy|sad|excited|calm|confident|empathetic|professional|sarcastic|angry|neutral|whispering|laughing|shocked|scared>",
  "emotion_source": "<auto|selected|combined>",
  "reasoning": "<one short phrase explaining the mood choice>"
}}"""


def build_mulberry_description(name: str, p: Personality, custom_vibe: str = "") -> str:
    """
    Generates the Silk mulberry voice description using vd.md vocabulary.
    The description sets the base voice character; emotion is appended per-call in tts/service.py.
    """
    pacing = "brisk" if p.energy == "chaotic" else "conversational"
    timbre = "warm" if p.tone == "sincere" else "smooth"
    register = "casual"
    accent = "hindi" if p.lang_lean == "hindi" else "indian"

    base = f"a {timbre} 20s {accent} accent voice, {pacing} pacing, {register} register"

    custom_vibe = custom_vibe.strip()
    if custom_vibe:
        base += f", {custom_vibe}"

    return base


# ─── Multi-profile store ──────────────────────────────────────────────────────

class UserProfileStore:
    """
    Manages multiple user profiles.

    get() / exists() — backward-compatible: operate on the active profile.
    get_all() / get_active_id() / activate() / delete() — multi-profile API.
    save() — creates new profile (or updates existing if profile_id given),
             always makes the saved profile active.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}
        self._active_id: Optional[str] = None
        self._load()

    # ── Backward-compat API ───────────────────────────────────────────────────

    def exists(self) -> bool:
        return self._active_id is not None and self._active_id in self._profiles

    def get(self) -> Optional[UserProfile]:
        if self._active_id:
            return self._profiles.get(self._active_id)
        return None

    def clear(self) -> None:
        """Remove the active profile."""
        if self._active_id and self._active_id in self._profiles:
            del self._profiles[self._active_id]
        self._active_id = next(iter(self._profiles), None)
        self._flush()

    # ── Multi-profile API ─────────────────────────────────────────────────────

    def get_all(self) -> list[UserProfile]:
        return list(self._profiles.values())

    def get_active_id(self) -> Optional[str]:
        return self._active_id

    def save(
        self,
        name: str,
        personality: Personality,
        custom_vibe: str = "",
        profile_id: Optional[str] = None,
    ) -> UserProfile:
        """
        Create a new profile (if profile_id is None or unknown)
        or update an existing one. Always activates the saved profile.
        """
        pid = profile_id if (profile_id and profile_id in self._profiles) else str(_uuid.uuid4())

        llm_prompt    = build_llm_system_prompt(name, personality, custom_vibe)
        mulberry_desc = build_mulberry_description(name, personality, custom_vibe)

        profile = UserProfile(
            profile_id=pid,
            name=name.strip(),
            personality=personality,
            custom_vibe=custom_vibe.strip(),
            llm_system_prompt=llm_prompt,
            mulberry_description=mulberry_desc,
        )
        self._profiles[pid] = profile
        self._active_id = pid
        self._flush()
        logger.info("Profile saved → %s (active)", pid)
        return profile

    def activate(self, profile_id: str) -> bool:
        if profile_id not in self._profiles:
            return False
        self._active_id = profile_id
        self._flush()
        logger.info("Activated profile → %s", profile_id)
        return True

    def delete(self, profile_id: str) -> bool:
        if profile_id not in self._profiles:
            return False
        del self._profiles[profile_id]
        if self._active_id == profile_id:
            self._active_id = next(iter(self._profiles), None)
        self._flush()
        logger.info("Deleted profile %s; active → %s", profile_id, self._active_id)
        return True

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if PROFILES_PATH.exists():
            try:
                raw = json.loads(PROFILES_PATH.read_text())
                self._active_id = raw.get("active_id")
                for pid, pdata in raw.get("profiles", {}).items():
                    self._profiles[pid] = UserProfile.from_dict(pdata)
                logger.info("Loaded %d profile(s)", len(self._profiles))
                return
            except Exception as exc:
                logger.warning("Could not load user_profiles.json: %s", exc)

        # Migrate from legacy single-profile file
        if LEGACY_PATH.exists():
            try:
                legacy = json.loads(LEGACY_PATH.read_text())
                pid = str(_uuid.uuid4())
                legacy["profile_id"] = pid
                profile = UserProfile.from_dict(legacy)
                self._profiles[pid] = profile
                self._active_id = pid
                self._flush()
                logger.info("Migrated legacy profile → %s", pid)
            except Exception as exc:
                logger.warning("Could not migrate legacy profile: %s", exc)

    def _flush(self) -> None:
        data = {
            "active_id": self._active_id,
            "profiles":  {pid: p.to_dict() for pid, p in self._profiles.items()},
        }
        PROFILES_PATH.write_text(json.dumps(data, indent=2))


# Singleton
user_profile_store = UserProfileStore()
