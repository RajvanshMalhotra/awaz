"""
llm/service.py — Gemini 2.0 Flash LLM for Awaaz v2

If a user profile exists (onboarding completed):
  - System prompt = profile.llm_system_prompt  (personality-tuned)
  - Each call also injects per-call context (relationship, mood, speaker name)

If no profile exists (fallback):
  - Uses the generic FALLBACK_SYSTEM_PROMPT
  - Behaviour identical to original service.py
"""

import json
import asyncio
from typing import Optional

from google import genai
from google.genai import types

from core.config import get_settings
from core.models import LLMResult, Relationship
from core.user_profile import user_profile_store

EMOTION_TAGS = [
    "laughing", "shocked", "whispering", "sad", "angry",
    "scared", "sarcastic", "happy", "neutral", "excited",
]

# ─── Fallback system prompt (used when no onboarding profile exists) ──────────

FALLBACK_SYSTEM_PROMPT = """You are an expressive text generator for a voice assistant.

Given a transcribed message, a relationship context, and an optional mood override:
1. Detect the emotional tone of the input message.
2. Write a warm, natural reply that fits the relationship and tone.
3. Format the reply using emotion tags like: (laughing)Hahaha...Thats so funny... (shocked)Wait...Ohmygod...

Language rules (STRICT):
- ALWAYS reply in Hinglish — Roman-script Hindi mixed naturally with English.
- Do NOT use Devanagari script. Every word must be ASCII/Roman only.
- Mix ratio should feel natural: Hindi words for emotion/warmth/fillers, English for clarity.
- Filler words: yaar, arre, bhai, sach mein, matlab, kya, acha, haan, bas

Rules for expressive text format:
- Use emotion tags from this list ONLY: {emotion_tags}
- Tags wrap the words that carry that emotion — switch tags mid-sentence if needed.
- Compress spaces within emotional bursts: "Oh my god" → "Ohmygod"
- Use ellipsis (...) to indicate natural speech pauses.
- Keep replies conversational length.
- The reply should feel like it comes from a real person, not an assistant.

Relationship affects tone:
- friend: casual, playful     | best_friend: zero filter, chaotic
- parent: warm, respectful    | sibling: banter-heavy, affectionate
- romantic: intimate          | colleague: friendly but measured
- boss: polite, professional  | stranger: polite, slightly formal

You MUST respond with valid JSON only. No markdown, no preamble.
Schema:
{{
  "expressive_text": "<reply using emotion tags>",
  "detected_mood": "<one word: dominant emotion in the INPUT>",
  "reasoning": "<one sentence: why you chose this tone>"
}}
""".format(emotion_tags=", ".join(EMOTION_TAGS))


class LLMService:
    """
    Gemini 2.0 Flash — tone detection + expressive Hinglish generation.

    On init, checks for a user profile and builds a personalised system prompt.
    Call reload_profile() if profile changes at runtime (e.g. after onboarding).
    """

    def __init__(self):
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model  = "gemini-2.0-flash"
        self._build_config()

    def _build_config(self):
        """Build GenerateContentConfig from user profile (or fallback)."""
        profile = user_profile_store.get()

        if profile:
            system_prompt = profile.llm_system_prompt
            self._profile_name = profile.name
        else:
            system_prompt = FALLBACK_SYSTEM_PROMPT
            self._profile_name = None

        self._config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.85,
            max_output_tokens=512,
            response_mime_type="application/json",
        )

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
        mood_override: Optional[str] = None,
        extra_text: Optional[str] = None,
    ) -> LLMResult:
        """
        Generate an expressive Hinglish reply.

        Args:
            transcript:    STT output — what the user said.
            relationship:  Context for tone calibration.
            mood_override: Force a specific emotion in the reply.
            extra_text:    Optional extra instruction.

        Returns:
            LLMResult with expressive_text, detected_mood, reasoning.
        """
        prompt = self._build_prompt(transcript, relationship, mood_override, extra_text)
        loop   = asyncio.get_running_loop()

        response = await loop.run_in_executor(
            None,
            lambda: self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=self._config,
            ),
        )

        return self._parse_response(response.text)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        transcript: str,
        relationship: Relationship,
        mood_override: Optional[str],
        extra_text: Optional[str],
    ) -> str:
        """
        Per-call context injected into every message.
        Includes profile name if available so the LLM knows who it's replying for.
        """
        lines = [
            f'Message: "{transcript}"',
            f"Relationship: {relationship.value}",
        ]

        # Per-call personality reinforcement from profile
        if self._profile_name:
            lines.append(f"Replying as {self._profile_name}'s voice assistant — stay true to their personality profile.")

        if mood_override and mood_override != "auto":
            lines.append(
                f"Mood override: Reply MUST use the '{mood_override}' emotion tag predominantly."
            )
        if extra_text:
            lines.append(f"Extra instruction: {extra_text}")

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
            raise ValueError(f"Gemini returned non-JSON: {raw!r}") from e
        return LLMResult(
            expressive_text=data["expressive_text"],
            detected_mood=data["detected_mood"],
            reasoning=data.get("reasoning", ""),
        )


# Singleton
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service