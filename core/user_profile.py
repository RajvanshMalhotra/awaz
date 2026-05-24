"""
core/user_profile.py — User personality profile for Awaaz v2

Stores onboarding data in user_profile.json (gitignored).

Schema stored on disk:
{
    "name": "Raj",
    "voice_gender": "male",
    "personality": {
        "energy":    "chaotic",      // chill | chaotic
        "filter":    "unfiltered",   // clean | unfiltered
        "style":     "dramatic",     // punchy | dramatic
        "tone":      "sarcastic",    // sincere | sarcastic
        "lang_lean": "hindi"         // hindi | english
    },
    "custom_vibe": "like a chaotic Delhi boy",
    "llm_system_prompt": "<generated full system prompt>",
    "mulberry_description": "<generated voice description for Silk>"
}
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal, Optional

from core.config import settings

logger = logging.getLogger(__name__)

PROFILE_PATH = Path(getattr(settings, "user_profile_path", "user_profile.json"))

# ─── Personality dimensions ───────────────────────────────────────────────────

Energy    = Literal["chill", "chaotic"]
Filter    = Literal["clean", "unfiltered"]
Style     = Literal["punchy", "dramatic"]
Tone      = Literal["sincere", "sarcastic"]
LangLean  = Literal["hindi", "english"]

VALID_VOICE_GENDERS = {"female", "female_alt", "male", "male_deep"}

GENDER_TO_SPEAKER = {
    "female":     "speaker_1",
    "female_alt": "speaker_2",
    "male":       "speaker_3",
    "male_deep":  "speaker_4",
}


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
    name:                str
    voice_gender:        str          # female | female_alt | male | male_deep
    personality:         Personality
    custom_vibe:         str          # free-text vibe refinement from onboarding
    llm_system_prompt:   str          # full generated system prompt → injected at LLM init
    mulberry_description: str         # voice description → sent to Silk per call

    def silk_speaker(self) -> str:
        return GENDER_TO_SPEAKER.get(self.voice_gender, "speaker_1")

    def to_dict(self) -> dict:
        return {
            "name":                  self.name,
            "voice_gender":          self.voice_gender,
            "personality":           self.personality.to_dict(),
            "custom_vibe":           self.custom_vibe,
            "llm_system_prompt":     self.llm_system_prompt,
            "mulberry_description":  self.mulberry_description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        return cls(
            name=d["name"],
            voice_gender=d["voice_gender"],
            personality=Personality.from_dict(d["personality"]),
            custom_vibe=d.get("custom_vibe", ""),
            llm_system_prompt=d["llm_system_prompt"],
            mulberry_description=d["mulberry_description"],
        )


# ─── Prompt + description generation ─────────────────────────────────────────

def build_llm_system_prompt(name: str, p: Personality, custom_vibe: str = "") -> str:
    """
    Generates a full LLM system prompt tailored to the user's personality.
    This replaces the generic system prompt in llm/service.py for this user.
    """

    # Energy (Extraversion — energized by people / uncertainty)
    energy_line = (
        "The user is extroverted and high-energy — they get charged up by people and chaos. "
        "Match that energy: be loud, fast, reactive, spontaneous. Don't hold back."
        if p.energy == "chaotic"
        else "The user is introverted and calm — they recharge alone and prefer measured interactions. "
        "Keep the vibe relaxed, unhurried, and warm. Don't over-react."
    )

    # Filter (Agreeableness inverse — can say no, speaks up when they disagree)
    filter_line = (
        "The user is direct and assertive — they say no easily and speak up when they disagree. "
        "Mirror this: be bold, use mild Hindi expletives naturally (bc, saale, bhai, teri) where they fit. "
        "Don't soften every edge."
        if p.filter == "unfiltered"
        else "The user is agreeable and keeps language clean. No expletives. "
        "Replies should be warm and non-confrontational."
    )

    # Style (Conscientiousness — planned and efficient vs procrastinating and dramatic)
    style_line = (
        "The user is conscientious and efficient. Keep replies SHORT and PUNCHY — "
        "they respect brevity. No unnecessary build-up. Hit the point and stop."
        if p.style == "punchy"
        else "The user is spontaneous and expressive. Go DRAMATIC — build up emotion, "
        "let it breathe, go filmy. They love a full arc even in a short reply."
    )

    # Tone (Neuroticism / Agreeableness — sensitive to criticism, avoids conflict = sincere)
    tone_line = (
        "The user is emotionally sensitive and conflict-averse — they feel things deeply. "
        "Replies should be warm, genuine, and emotionally present. Never cold or dismissive."
        if p.tone == "sincere"
        else "The user has thick skin and doesn't take things personally. "
        "Their default is dry, sarcastic humour. Lean into deadpan delivery and subtle roasts — "
        "they can handle it and actually prefer it."
    )

    # Language lean (Openness / self-trust — explores new ideas, trusts own judgment)
    lang_line = (
        "The user is open and self-assured — they trust their instincts over convention. "
        "Lean HEAVILY Hindi: yaar, arre, bhai, matlab, kya bakwaas, sach mein, acha sun. "
        "English only when it genuinely fits."
        if p.lang_lean == "hindi"
        else "The user thinks in a more English-dominant frame. Keep Hinglish natural but "
        "lean slightly English. Hindi for warmth and fillers only."
    )

    custom_vibe = custom_vibe.strip()
    custom_vibe_section = (
        "\nCUSTOM VIBE REFINEMENT:\n"
        f"- The user described their vibe as: \"{custom_vibe}\". "
        "Treat this as an extra layer on top of the personality profile. "
        "Use it to refine word choice, pacing, humour, and cultural flavour, while still following all core rules.\n"
        if custom_vibe
        else ""
    )

    return f"""You are an expressive voice assistant replying on behalf of {name}'s phone.

PERSONALITY PROFILE FOR {name.upper()}:
- {energy_line}
- {filter_line}
- {style_line}
- {tone_line}
- {lang_line}
{custom_vibe_section}

CORE RULES (never break these):
1. ALWAYS reply in Hinglish — Roman script only. Zero Devanagari.
2. Use emotion tags from this list ONLY: laughing, shocked, whispering, sad, angry, scared, sarcastic, happy, neutral, excited
3. Format: (emotion)Text...(emotion)Text... — switch tags mid-reply as mood shifts.
4. Compress emotional bursts: "Oh my god" → "Ohmygod", "yaar sun" → "yaarsun"
5. Use ellipsis (...) for natural pauses and trailing off.
6. Relationship context shapes tone — friend is casual, romantic is intimate, boss is measured.
7. Never break character. Never sound like an AI assistant.

OUTPUT — valid JSON only, no markdown:
{{
  "expressive_text": "<reply using emotion tags>",
  "detected_mood": "<dominant emotion you detected in the INPUT — one word>",
  "reasoning": "<one sentence: why you chose this tone>"
}}"""


def build_mulberry_description(name: str, p: Personality, voice_gender: str, custom_vibe: str = "") -> str:
    """
    Generates the Silk mulberry voice description.
    This is sent per-call to steer how the voice sounds.
    """
    gender_base = "female" if voice_gender in ("female", "female_alt") else "male"

    energy_desc  = "high-energy, fast-paced" if p.energy == "chaotic" else "calm, relaxed"
    style_desc   = "punchy and clipped" if p.style == "punchy" else "expressive and dramatic"
    tone_desc    = "dry and sardonic" if p.tone == "sarcastic" else "warm and sincere"
    lang_desc    = "heavily Hindi-accented Hinglish" if p.lang_lean == "hindi" else "natural Hinglish with slight English lean"

    base_description = (
        f"{gender_base} voice, {energy_desc}, {style_desc}, {tone_desc}, "
        f"conversational {lang_desc}, like talking to a close friend"
    )
    custom_vibe = custom_vibe.strip()
    if custom_vibe:
        return f"{base_description}, with the user's custom vibe: {custom_vibe}"
    return base_description


# ─── Store ────────────────────────────────────────────────────────────────────

class UserProfileStore:
    def __init__(self, path: Path = PROFILE_PATH):
        self._path    = path
        self._profile: Optional[UserProfile] = None

    def exists(self) -> bool:
        return self._path.exists()

    def get(self) -> Optional[UserProfile]:
        if self._profile is None and self._path.exists():
            self._load()
        return self._profile

    def save(
        self,
        name: str,
        voice_gender: str,
        personality: Personality,
        custom_vibe: str = "",
    ) -> UserProfile:
        if voice_gender not in VALID_VOICE_GENDERS:
            raise ValueError(f"voice_gender must be one of {VALID_VOICE_GENDERS}")

        llm_prompt   = build_llm_system_prompt(name, personality, custom_vibe)
        mulberry_desc = build_mulberry_description(
            name, personality, voice_gender, custom_vibe
        )

        profile = UserProfile(
            name=name.strip(),
            voice_gender=voice_gender,
            personality=personality,
            custom_vibe=custom_vibe.strip(),
            llm_system_prompt=llm_prompt,
            mulberry_description=mulberry_desc,
        )
        self._profile = profile
        self._flush()
        logger.info("User profile saved → %s", self._path)
        return profile

    def clear(self) -> None:
        self._profile = None
        if self._path.exists():
            self._path.unlink()

    def _load(self) -> None:
        try:
            self._profile = UserProfile.from_dict(json.loads(self._path.read_text()))
        except Exception as exc:
            logger.warning("Could not load user profile: %s", exc)
            self._profile = None

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._profile.to_dict(), indent=2))


# Singleton
user_profile_store = UserProfileStore()
