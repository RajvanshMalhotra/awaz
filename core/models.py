from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Mood(str, Enum):
    auto = "auto"              # infer from text
    happy = "happy"
    sad = "sad"
    excited = "excited"
    calm = "calm"
    confident = "confident"
    empathetic = "empathetic"
    professional = "professional"
    sarcastic = "sarcastic"
    angry = "angry"
    neutral = "neutral"
    whispering = "whispering"


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
# Core pipeline
# ---------------------------------------------------------------------------

class ProcessRequest(BaseModel):
    relationship: Relationship = Relationship.friend
    mood_override: Mood = Mood.auto
    extra_text: Optional[str] = None


class LLMResult(BaseModel):
    expressive_text: str            # original text with (emotion) tags added
    detected_mood: str              # primary emotion applied
    emotion_source: str = "auto"   # "auto" | "selected" | "combined"
    reasoning: str                  # e.g. "Auto-inferred: calm" or "Using selected mood: confident"


class ProcessResponse(BaseModel):
    transcript: str
    detected_language: Optional[str] = None
    effective_relationship: Relationship
    relationship_source: str
    llm: LLMResult
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
# Onboarding
# ---------------------------------------------------------------------------

Energy = Literal["chill", "chaotic"]
Filter = Literal["clean", "unfiltered"]
Style = Literal["punchy", "dramatic"]
Tone = Literal["sincere", "sarcastic"]
LangLean = Literal["hindi", "english"]


class PersonalityRequest(BaseModel):
    energy: Energy
    filter: Filter
    style: Style
    tone: Tone
    lang_lean: LangLean


class OnboardingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    personality: PersonalityRequest
    custom_vibe: str = Field(default="", max_length=400)
    profile_id: Optional[str] = None  # if given, update existing profile


class OnboardingResponse(BaseModel):
    profile_id: str
    name: str
    personality: dict
    custom_vibe: str
    llm_system_prompt: str
    mulberry_description: str


class OnboardingStatusResponse(BaseModel):
    completed: bool
    profile: Optional[OnboardingResponse] = None


class ProfileListResponse(BaseModel):
    active_id: Optional[str]
    profiles: list[OnboardingResponse]
