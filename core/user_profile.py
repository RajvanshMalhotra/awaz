# """
# core/user_profile.py — User personality profile for Awaaz v2

# Stores onboarding data in user_profile.json (gitignored).

# Schema stored on disk:
# {
#     "name": "Raj",
#     "voice_gender": "male",
#     "personality": {
#         "energy":    "chaotic",      // chill | chaotic
#         "filter":    "unfiltered",   // clean | unfiltered
#         "style":     "dramatic",     // punchy | dramatic
#         "tone":      "sarcastic",    // sincere | sarcastic
#         "lang_lean": "hindi"         // hindi | english
#     },
#     "custom_vibe": "like a chaotic Delhi boy",
#     "llm_system_prompt": "<generated full system prompt>",
#     "mulberry_description": "<generated voice description for Silk>"
# }
# """

# from __future__ import annotations

# import json
# import logging
# from dataclasses import dataclass, asdict
# from pathlib import Path
# from typing import Literal, Optional

# from core.config import settings

# logger = logging.getLogger(__name__)

# PROFILE_PATH = Path(getattr(settings, "user_profile_path", "user_profile.json"))

# # ─── Personality dimensions ───────────────────────────────────────────────────

# Energy    = Literal["chill", "chaotic"]
# Filter    = Literal["clean", "unfiltered"]
# Style     = Literal["punchy", "dramatic"]
# Tone      = Literal["sincere", "sarcastic"]
# LangLean  = Literal["hindi", "english"]

# VALID_VOICE_GENDERS = {"female", "female_alt", "male", "male_deep"}

# GENDER_TO_SPEAKER = {
#     "female":     "speaker_1",
#     "female_alt": "speaker_2",
#     "male":       "speaker_3",
#     "male_deep":  "speaker_4",
# }


# @dataclass
# class Personality:
#     energy:    Energy
#     filter:    Filter
#     style:     Style
#     tone:      Tone
#     lang_lean: LangLean

#     def to_dict(self) -> dict:
#         return asdict(self)

#     @classmethod
#     def from_dict(cls, d: dict) -> "Personality":
#         return cls(**d)


# @dataclass
# class UserProfile:
#     name:                str
#     voice_gender:        str          # female | female_alt | male | male_deep
#     personality:         Personality
#     custom_vibe:         str          # free-text vibe refinement from onboarding
#     llm_system_prompt:   str          # full generated system prompt → injected at LLM init
#     mulberry_description: str         # voice description → sent to Silk per call

#     def silk_speaker(self) -> str:
#         return GENDER_TO_SPEAKER.get(self.voice_gender, "speaker_1")

#     def to_dict(self) -> dict:
#         return {
#             "name":                  self.name,
#             "voice_gender":          self.voice_gender,
#             "personality":           self.personality.to_dict(),
#             "custom_vibe":           self.custom_vibe,
#             "llm_system_prompt":     self.llm_system_prompt,
#             "mulberry_description":  self.mulberry_description,
#         }

#     @classmethod
#     def from_dict(cls, d: dict) -> "UserProfile":
#         return cls(
#             name=d["name"],
#             voice_gender=d["voice_gender"],
#             personality=Personality.from_dict(d["personality"]),
#             custom_vibe=d.get("custom_vibe", ""),
#             llm_system_prompt=d["llm_system_prompt"],
#             mulberry_description=d["mulberry_description"],
#         )


# # ─── Prompt + description generation ─────────────────────────────────────────

# def build_llm_system_prompt(name: str, p: Personality, custom_vibe: str = "") -> str:
#     """
#     Generates a full LLM system prompt tailored to the user's personality.
#     This replaces the generic system prompt in llm/service.py for this user.
#     """

#     # Energy (Extraversion — energized by people / uncertainty)
#     energy_line = (
#         "The user is extroverted and high-energy — they get charged up by people and chaos. "
#         "Match that energy: be loud, fast, reactive, spontaneous. Don't hold back."
#         if p.energy == "chaotic"
#         else "The user is introverted and calm — they recharge alone and prefer measured interactions. "
#         "Keep the vibe relaxed, unhurried, and warm. Don't over-react."
#     )

#     # Filter (Agreeableness inverse — can say no, speaks up when they disagree)
#     filter_line = (
#         "The user is direct and assertive — they say no easily and speak up when they disagree. "
#         "Mirror this: be bold, use mild Hindi expletives naturally (bc, saale, bhai, teri) where they fit. "
#         "Don't soften every edge."
#         if p.filter == "unfiltered"
#         else "The user is agreeable and keeps language clean. No expletives. "
#         "Replies should be warm and non-confrontational."
#     )

#     # Style (Conscientiousness — planned and efficient vs procrastinating and dramatic)
#     style_line = (
#         "The user is conscientious and efficient. Keep replies SHORT and PUNCHY — "
#         "they respect brevity. No unnecessary build-up. Hit the point and stop."
#         if p.style == "punchy"
#         else "The user is spontaneous and expressive. Go DRAMATIC — build up emotion, "
#         "let it breathe, go filmy. They love a full arc even in a short reply."
#     )

#     # Tone (Neuroticism / Agreeableness — sensitive to criticism, avoids conflict = sincere)
#     tone_line = (
#         "The user is emotionally sensitive and conflict-averse — they feel things deeply. "
#         "Replies should be warm, genuine, and emotionally present. Never cold or dismissive."
#         if p.tone == "sincere"
#         else "The user has thick skin and doesn't take things personally. "
#         "Their default is dry, sarcastic humour. Lean into deadpan delivery and subtle roasts — "
#         "they can handle it and actually prefer it."
#     )

#     # Language lean (Openness / self-trust — explores new ideas, trusts own judgment)
#     lang_line = (
#         "The user is open and self-assured — they trust their instincts over convention. "
#         "Lean HEAVILY Hindi: yaar, arre, bhai, matlab, kya bakwaas, sach mein, acha sun. "
#         "English only when it genuinely fits."
#         if p.lang_lean == "hindi"
#         else "The user thinks in a more English-dominant frame. Keep Hinglish natural but "
#         "lean slightly English. Hindi for warmth and fillers only."
#     )

#     custom_vibe = custom_vibe.strip()
#     custom_vibe_section = (
#         "\nCUSTOM VIBE REFINEMENT:\n"
#         f"- The user described their vibe as: \"{custom_vibe}\". "
#         "Treat this as an extra layer on top of the personality profile. "
#         "Use it to refine word choice, pacing, humour, and cultural flavour, while still following all core rules.\n"
#         if custom_vibe
#         else ""
#     )

#     return f"""You are an expressive voice assistant replying on behalf of {name}'s phone.

# PERSONALITY PROFILE FOR {name.upper()}:
# - {energy_line}
# - {filter_line}
# - {style_line}
# - {tone_line}
# - {lang_line}
# {custom_vibe_section}

# CORE RULES (never break these):
# 1. ALWAYS reply in Hinglish — Roman script only. Zero Devanagari.
# 2. Use emotion tags from this list ONLY: laughing, shocked, whispering, sad, angry, scared, sarcastic, happy, neutral, excited
# 3. Format: (emotion)Text...(emotion)Text... — switch tags mid-reply as mood shifts.
# 4. Compress emotional bursts: "Oh my god" → "Ohmygod", "yaar sun" → "yaarsun"
# 5. Use ellipsis (...) for natural pauses and trailing off.
# 6. Relationship context shapes tone — friend is casual, romantic is intimate, boss is measured.
# 7. Never break character. Never sound like an AI assistant.

# OUTPUT — valid JSON only, no markdown:
# {{
#   "expressive_text": "<reply using emotion tags>",
#   "detected_mood": "<dominant emotion you detected in the INPUT — one word>",
#   "reasoning": "<one sentence: why you chose this tone>"
# }}"""


# def build_mulberry_description(name: str, p: Personality, voice_gender: str, custom_vibe: str = "") -> str:
#     """
#     Generates the Silk mulberry voice description.
#     This is sent per-call to steer how the voice sounds.
#     """
#     gender_base = "female" if voice_gender in ("female", "female_alt") else "male"

#     energy_desc  = "high-energy, fast-paced" if p.energy == "chaotic" else "calm, relaxed"
#     style_desc   = "punchy and clipped" if p.style == "punchy" else "expressive and dramatic"
#     tone_desc    = "dry and sardonic" if p.tone == "sarcastic" else "warm and sincere"
#     lang_desc    = "heavily Hindi-accented Hinglish" if p.lang_lean == "hindi" else "natural Hinglish with slight English lean"

#     base_description = (
#         f"{gender_base} voice, {energy_desc}, {style_desc}, {tone_desc}, "
#         f"conversational {lang_desc}, like talking to a close friend"
#     )
#     custom_vibe = custom_vibe.strip()
#     if custom_vibe:
#         return f"{base_description}, with the user's custom vibe: {custom_vibe}"
#     return base_description


# # ─── Store ────────────────────────────────────────────────────────────────────

# class UserProfileStore:
#     def __init__(self, path: Path = PROFILE_PATH):
#         self._path    = path
#         self._profile: Optional[UserProfile] = None

#     def exists(self) -> bool:
#         return self._path.exists()

#     def get(self) -> Optional[UserProfile]:
#         if self._profile is None and self._path.exists():
#             self._load()
#         return self._profile

#     def save(
#         self,
#         name: str,
#         voice_gender: str,
#         personality: Personality,
#         custom_vibe: str = "",
#     ) -> UserProfile:
#         if voice_gender not in VALID_VOICE_GENDERS:
#             raise ValueError(f"voice_gender must be one of {VALID_VOICE_GENDERS}")

#         llm_prompt   = build_llm_system_prompt(name, personality, custom_vibe)
#         mulberry_desc = build_mulberry_description(
#             name, personality, voice_gender, custom_vibe
#         )

#         profile = UserProfile(
#             name=name.strip(),
#             voice_gender=voice_gender,
#             personality=personality,
#             custom_vibe=custom_vibe.strip(),
#             llm_system_prompt=llm_prompt,
#             mulberry_description=mulberry_desc,
#         )
#         self._profile = profile
#         self._flush()
#         logger.info("User profile saved → %s", self._path)
#         return profile

#     def clear(self) -> None:
#         self._profile = None
#         if self._path.exists():
#             self._path.unlink()

#     def _load(self) -> None:
#         try:
#             self._profile = UserProfile.from_dict(json.loads(self._path.read_text()))
#         except Exception as exc:
#             logger.warning("Could not load user profile: %s", exc)
#             self._profile = None

#     def _flush(self) -> None:
#         self._path.parent.mkdir(parents=True, exist_ok=True)
#         self._path.write_text(json.dumps(self._profile.to_dict(), indent=2))


# # Singleton
# user_profile_store = UserProfileStore()
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
    Generates a personality-aware emotion-tagger system prompt.
    The LLM only adds emotion tags to the user's exact text — never rewrites content.
    """
    # Personality shapes which emotions to prefer, not what words to generate
    energy_hint = (
        "Prefer energetic emotions: excited, happy, confident, laughing."
        if p.energy == "chaotic"
        else "Prefer measured emotions: calm, neutral, empathetic, professional."
    )

    tone_hint = (
        "When tone is ambiguous, lean sarcastic or dry over sincere."
        if p.tone == "sarcastic"
        else "When tone is ambiguous, lean warm and sincere."
    )

    filter_hint = (
        "The user is bold and direct — angry or unfiltered emotions are acceptable when appropriate."
        if p.filter == "unfiltered"
        else "Keep emotion tags measured — avoid angry or aggressive choices."
    )

    custom_vibe = custom_vibe.strip()
    vibe_section = f"\nPersonality vibe context: {custom_vibe}" if custom_vibe else ""

    inline_tags = ", ".join([
        "<laugh>", "<laugh_harder>", "<chuckle>", "<giggle>", "<snort>",
        "<sigh>", "<exhale>", "<gasp>", "<gulp>",
        "<excited>", "<angry>", "<whisper>", "<cry>", "<scream>",
        "<sarcastic>", "<curious>",
    ])

    return f"""You are an emotion delivery enhancer for Silk mulberry TTS, calibrated for {name}.

Your ONLY job: Insert Mulberry inline tags into the user's EXACT text to add expressive delivery.

STRICT RULES:
1. NEVER rewrite, rephrase, expand, or shorten the user's text.
2. NEVER change vocabulary, sentence structure, or word order.
3. Preserve EVERY word from the original text exactly as given.
4. ONLY insert inline tags — they trigger sounds in TTS, not words.

Available inline tags: {inline_tags}

PERSONALITY CALIBRATION FOR {name.upper()}:
- {energy_hint}
- {tone_hint}
- {filter_hint}{vibe_section}

Tagging rules:
- Drop a tag at the moment a natural sound or expression would occur
- Place the tag right at that moment: "seriously? <gasp> I can't believe this"
- Use 1–3 tags maximum — too many sounds unnatural
- Tags are sounds, not labels — <laugh> makes it laugh, <sigh> makes it sigh

Mood handling:
- If mood_override is "auto": infer the best tags from the text's natural tone + personality
- If mood_override is specified: prefer tags that match that mood
- Set emotion_source to "auto", "selected", or "combined" accordingly

OUTPUT — valid JSON only, no markdown:
{{
  "expressive_text": "<original text with <inline_tags> inserted at expression moments>",
  "detected_mood": "<primary emotion: happy|sad|excited|calm|confident|empathetic|professional|sarcastic|angry|neutral|whispering|laughing|shocked|scared>",
  "emotion_source": "<auto|selected|combined>",
  "reasoning": "<short phrase: e.g. Auto-inferred: calm or Using selected mood: confident>"
}}"""


def build_mulberry_description(name: str, p: Personality, custom_vibe: str = "") -> str:
    """
    Generates the Silk mulberry voice description using vd.md vocabulary.
    The description sets the base voice character; emotion is appended per-call in tts/service.py.
    """
    # Pacing (vd.md: very slow | slow | conversational | brisk | fast | very_fast)
    pacing = "brisk" if p.energy == "chaotic" else "conversational"

    # Timbre (vd.md: deep | warm | gravelly | smooth | raspy | nasal | harsh | whisper)
    timbre = "warm" if p.tone == "sincere" else "smooth"

    # Register (vd.md: formal | neutral | casual)
    register = "casual"

    # Accent (vd.md Indian regional: hindi | punjabi | ...)
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