from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Mood(str, Enum):
    auto = "auto"          # LLM detects mood from audio/transcript
    happy = "happy"
    sad = "sad"
    shocked = "shocked"
    sarcastic = "sarcastic"
    angry = "angry"
    scared = "scared"
    laughing = "laughing"
    whispering = "whispering"
    neutral = "neutral"
    excited = "excited"


class Relationship(str, Enum):
    friend = "friend"
    best_friend = "best_friend"
    parent = "parent"
    sibling = "sibling"
    romantic = "romantic"
    colleague = "colleague"
    boss = "boss"
    stranger = "stranger"


# ---------------------------------------------------------------------------
# STT
# ---------------------------------------------------------------------------

class STTResult(BaseModel):
    transcript: str
    detected_language: Optional[str] = None


# ---------------------------------------------------------------------------
# Speaker
# ---------------------------------------------------------------------------

class SpeakerProfile(BaseModel):
    speaker_id: str
    name: str
    relationship: Relationship              # stored alongside voice print
    embedding: list[float]                  # resemblyzer 256-d embedding
    created_at: str


class SpeakerRecognitionResult(BaseModel):
    speaker_id: Optional[str] = None       # None = unknown speaker
    name: Optional[str] = None
    relationship: Optional[Relationship] = None  # auto-detected from saved profile
    similarity: float                      # 0–1
    is_new_speaker: bool                   # True = frontend should prompt to save


class SaveSpeakerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    relationship: Relationship = Relationship.friend
    # audio sent as form-data via /pipeline/save-speaker


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

class ProcessRequest(BaseModel):
    """
    Sent alongside the audio file (multipart form).
    Frontend sends these as JSON-encoded form field or query params.
    """
    relationship: Relationship = Relationship.friend
    mood_override: Mood = Mood.auto          # auto = let LLM decide
    extra_text: Optional[str] = None         # keyboard input from user
    speaker_name_if_new: Optional[str] = None  # if user pre-named a new speaker


class LLMResult(BaseModel):
    expressive_text: str            # (laughing)Haha... format
    detected_mood: str              # raw string — LLM may return values outside Mood enum
    reasoning: str                  # short internal note, useful for deny-regen


class ProcessResponse(BaseModel):
    # STT
    transcript: str
    detected_language: Optional[str] = None

    # Speaker
    speaker: SpeakerRecognitionResult
    save_voice_prompt: bool         # True = show "Save this voice?" UI

    # Relationship — auto-detected from speaker profile if known
    effective_relationship: Relationship
    relationship_source: str        # "speaker_profile" | "frontend_override" | "default"

    # LLM
    llm: LLMResult

    # Session token for approve/deny
    session_id: str


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------

class ApproveRequest(BaseModel):
    session_id: str


class ApproveResponse(BaseModel):
    tts_audio_url: Optional[str] = None    # populated when TTS is available
    tts_payload: dict               # raw payload forwarded to TTS
    expressive_text: str


# ---------------------------------------------------------------------------
# Deny / Regenerate
# ---------------------------------------------------------------------------

class DenyRequest(BaseModel):
    session_id: str
    mood_override: Optional[Mood] = None
    relationship_override: Optional[Relationship] = None
    extra_text: Optional[str] = None     # user typed clarification


class DenyResponse(BaseModel):
    llm: LLMResult
    session_id: str                      # new session_id for next approve/deny


# ---------------------------------------------------------------------------
# Save speaker (called after user confirms)
# ---------------------------------------------------------------------------

class SaveSpeakerResponse(BaseModel):
    speaker_id: str
    name: str
    relationship: Relationship
    message: str


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

Energy = Literal["chill", "chaotic"]
Filter = Literal["clean", "unfiltered"]
Style = Literal["punchy", "dramatic"]
Tone = Literal["sincere", "sarcastic"]
LangLean = Literal["hindi", "english"]
VoiceGender = Literal["female", "female_alt", "male", "male_deep"]


class PersonalityRequest(BaseModel):
    energy: Energy
    filter: Filter
    style: Style
    tone: Tone
    lang_lean: LangLean


class OnboardingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    voice_gender: VoiceGender
    personality: PersonalityRequest
    custom_vibe: str = Field(default="", max_length=400)


class OnboardingResponse(BaseModel):
    name: str
    voice_gender: str
    personality: dict
    custom_vibe: str
    llm_system_prompt: str
    mulberry_description: str
    silk_speaker: str


class OnboardingStatusResponse(BaseModel):
    completed: bool
    profile: Optional[OnboardingResponse] = None
