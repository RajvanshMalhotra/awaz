"""
llm/service.py - Groq Llama LLM for Awaaz v2

If a user profile exists (onboarding completed):
  - System prompt = profile.llm_system_prompt  (personality-tuned)
  - Each call also injects per-call context (relationship, mood, speaker name)

If no profile exists (fallback):
  - Uses the generic FALLBACK_SYSTEM_PROMPT
  - Behaviour identical to original service.py
"""

import json
from typing import Optional

from groq import AsyncGroq

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
    Groq-hosted Llama - tone detection + expressive Hinglish generation.

    On init, checks for a user profile and builds a personalised system prompt.
    Call reload_profile() if profile changes at runtime (e.g. after onboarding).
    """

    def __init__(self):
        settings = get_settings()
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.groq_llm_model
        self._build_config()

    def _build_config(self):
        """Build the system prompt from user profile (or fallback)."""
        profile = user_profile_store.get()

        if profile:
            personality_traits = profile.personality.to_dict()
            traits_text = "\n".join(
                f"- {key}: {value}" for key, value in personality_traits.items()
            )
            custom_vibe = profile.custom_vibe.strip() or "none"
            self._system_prompt = (
                f"{profile.llm_system_prompt}\n\n"
                "EXTRACTED PERSONALITY TRAITS (always use these when replying):\n"
                f"{traits_text}\n"
                f"- custom_vibe: {custom_vibe}\n"
                f"- voice_gender: {profile.voice_gender}"
            )
            self._profile_name = profile.name
            self._personality_traits = personality_traits
            self._custom_vibe = profile.custom_vibe.strip()
        else:
            self._system_prompt = FALLBACK_SYSTEM_PROMPT
            self._profile_name = None
            self._personality_traits = None
            self._custom_vibe = ""

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
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
            max_tokens=512,
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
        """
        Per-call context injected into every message.
        Includes profile name if available so the LLM knows who it's replying for.
        """
        lines = [
            f'Message: "{transcript}"',
            f"Relationship: {relationship.value}",
        ]
        if speaker_name:
            lines.append(f"Identified speaker name: {speaker_name}")

        # Per-call personality reinforcement from profile
        if self._profile_name:
            lines.append(
                f"Replying as {self._profile_name}'s voice assistant - stay true to their personality profile."
            )
        if self._personality_traits:
            traits = ", ".join(
                f"{key}={value}" for key, value in self._personality_traits.items()
            )
            lines.append(f"Extracted personality traits: {traits}")
        if self._custom_vibe:
            lines.append(f"Custom vibe refinement: {self._custom_vibe}")

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
            raise ValueError(f"Groq Llama returned non-JSON: {raw!r}") from e
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
