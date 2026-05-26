"""
llm/service.py - Groq Llama LLM for Awaaz v2

If a user profile exists (onboarding completed):
  - System prompt = profile.llm_system_prompt  (personality-tuned, built once at init)
  - Per-call context adds only: relationship, speaker name, mood override, extra text
  - Personality traits are NOT re-injected per call — they're already in the system prompt

If no profile exists (fallback):
  - Uses the generic EMOTION_TAGGER_PROMPT
  - Behaviour identical to original service.py
"""

import json
from typing import Optional

from groq import AsyncGroq

from core.config import get_settings
from core.models import LLMResult, Relationship
from core.user_profile import user_profile_store

# Mulberry's actual inline tag vocabulary (from vd.md)
MULBERRY_INLINE_TAGS = [
    "laugh", "laugh_harder", "chuckle", "giggle", "snort",
    "sigh", "exhale", "gasp", "gulp",
    "excited", "angry", "whisper", "cry", "scream", "sing",
    "sarcastic", "curious",
]

# Mood → which inline tags are most appropriate (guides the LLM)
MOOD_TAG_HINTS: dict[str, list[str]] = {
    "happy":        ["chuckle", "giggle"],
    "sad":          ["sigh", "cry"],
    "excited":      ["excited", "gasp"],
    "calm":         ["exhale", "sigh"],
    "confident":    [],
    "empathetic":   ["sigh"],
    "professional": [],
    "sarcastic":    ["sarcastic"],
    "angry":        ["angry"],
    "neutral":      [],
    "whispering":   ["whisper"],
    "laughing":     ["laugh", "laugh_harder", "chuckle", "giggle"],
    "shocked":      ["gasp", "scream"],
    "scared":       ["gasp", "cry"],
}

# ─── Fallback prompt (no profile) ────────────────────────────────────────────

FALLBACK_PROMPT = """You are a voice assistant for someone who is unable to speak.

YOUR JOB: Take what the user wants to say and generate a natural, expressive spoken response in Hinglish. Then insert Mulberry inline tags to make the TTS delivery expressive.

RULES:
1. Keep the core meaning — do not change the topic or add unrelated content
2. Rephrase into natural spoken Hinglish — conversational, not written
3. Keep it concise: 1–3 sentences maximum
4. Insert 1–3 Mulberry inline tags at moments where a natural sound/expression fits
5. Always reply in Roman script only (no Devanagari)
6. If mood_override is set, match that emotional tone in the words and tags

Available inline tags: {tags}

OUTPUT — valid JSON only, no markdown:
{{
  "expressive_text": "<the spoken response with <inline_tags> inserted>",
  "detected_mood": "<primary emotion: happy|sad|excited|calm|confident|empathetic|professional|sarcastic|angry|neutral|whispering|laughing|shocked|scared>",
  "emotion_source": "<auto|selected|combined>",
  "reasoning": "<one short phrase explaining the mood choice>"
}}""".format(tags=", ".join(f"<{t}>" for t in MULBERRY_INLINE_TAGS))


class LLMService:
    """
    Groq-hosted Llama — tone detection + expressive Hinglish generation.

    On init, checks for a user profile and builds a personalised system prompt.
    The system prompt carries the full personality — per-call prompts only add
    call-specific context (relationship, speaker, mood override).

    Call reload_profile() if profile changes at runtime (e.g. after onboarding).
    """

    def __init__(self):
        settings = get_settings()
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model  = settings.groq_llm_model
        self._build_config()

    def _build_config(self):
        """Regenerate system prompt from current profile personality (or fallback).
        Always regenerates — never uses the cached llm_system_prompt in the profile file —
        so changes to build_llm_system_prompt take effect without re-onboarding."""
        from core.user_profile import build_llm_system_prompt
        profile = user_profile_store.get()

        if profile:
            self._system_prompt = build_llm_system_prompt(
                profile.name, profile.personality, profile.custom_vibe
            )
            self._profile_name = profile.name
        else:
            self._system_prompt = FALLBACK_PROMPT
            self._profile_name  = None

    def reload_profile(self):
        """Call this after onboarding completes to pick up the new profile."""
        self._build_config()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        transcript: str,
        relationship: Relationship,
        speaker_name: Optional[str] = None,
        mood_override: Optional[str] = None,
        extra_text: Optional[str] = None,
    ) -> LLMResult:
        """
        Generate an expressive Hinglish reply.

        Args:
            transcript:    STT output — what the user said.
            relationship:  Context for tone calibration.
            speaker_name:  Identified speaker name, if known.
            mood_override: Force a specific emotion in the reply.
            extra_text:    Optional extra instruction.

        Returns:
            LLMResult with expressive_text, detected_mood, reasoning.
        """
        prompt = self._build_prompt(
            transcript, relationship, speaker_name, mood_override, extra_text
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.7,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return self._parse_response(content or "")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        transcript: str,
        relationship: Relationship,
        speaker_name: Optional[str],
        mood_override: Optional[str],
        extra_text: Optional[str],
    ) -> str:
        mood = mood_override or "auto"
        lines = [
            f'What {self._profile_name or "the user"} wants to say: "{transcript}"',
            f"mood_override: {mood}",
        ]

        hints = MOOD_TAG_HINTS.get(mood, [])
        if hints:
            lines.append(f"Suggested tags for this mood: {', '.join(f'<{t}>' for t in hints)}")

        if extra_text:
            lines.append(f"Additional context: {extra_text}")

        return "\n".join(lines)

    @staticmethod
    def _parse_response(raw: str) -> LLMResult:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1]
            clean = clean.rsplit("```", 1)[0].strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError as e:
            raise ValueError(f"Groq Llama returned non-JSON: {raw!r}") from e
        return LLMResult(
            expressive_text=data["expressive_text"],
            detected_mood=data["detected_mood"],
            emotion_source=data.get("emotion_source", "auto"),
            reasoning=data.get("reasoning", ""),
        )


# Singleton
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
