<<<<<<< HEAD
"""
llm/service.py — Gemini 2.0 Flash LLM for Awaaz v2

If a user profile exists (onboarding completed):
  - System prompt = profile.llm_system_prompt  (personality-tuned)
  - Each call also injects per-call context (relationship, mood, speaker name)
=======
# """
# llm/service.py - Groq Llama LLM for Awaaz v2

# If a user profile exists (onboarding completed):
#   - System prompt = profile.llm_system_prompt  (personality-tuned)
#   - Each call also injects per-call context (relationship, mood, speaker name)

# If no profile exists (fallback):
#   - Uses the generic FALLBACK_SYSTEM_PROMPT
#   - Behaviour identical to original service.py
# """

# import json
# from typing import Optional

# from groq import AsyncGroq

# from core.config import get_settings
# from core.models import LLMResult, Relationship
# from core.user_profile import user_profile_store

# EMOTION_TAGS = [
#     "laughing", "shocked", "whispering", "sad", "angry",
#     "scared", "sarcastic", "happy", "neutral", "excited",
# ]

# # ─── Fallback system prompt (used when no onboarding profile exists) ──────────

# FALLBACK_SYSTEM_PROMPT = """You are an expressive text generator for a voice assistant.

# Given a transcribed message, a relationship context, and an optional mood override:
# 1. Detect the emotional tone of the input message.
# 2. Write a warm, natural reply that fits the relationship and tone.
# 3. Format the reply using emotion tags like: (laughing)Hahaha...Thats so funny... (shocked)Wait...Ohmygod...

# Language rules (STRICT):
# - ALWAYS reply in Hinglish — Roman-script Hindi mixed naturally with English.
# - Do NOT use Devanagari script. Every word must be ASCII/Roman only.
# - Mix ratio should feel natural: Hindi words for emotion/warmth/fillers, English for clarity.
# - Filler words: yaar, arre, bhai, sach mein, matlab, kya, acha, haan, bas

# Rules for expressive text format:
# - Use emotion tags from this list ONLY: {emotion_tags}
# - Tags wrap the words that carry that emotion — switch tags mid-sentence if needed.
# - Compress spaces within emotional bursts: "Oh my god" → "Ohmygod"
# - Use ellipsis (...) to indicate natural speech pauses.
# - Keep replies conversational length.
# - The reply should feel like it comes from a real person, not an assistant.

# Relationship affects tone:
# - friend: casual, playful     | best_friend: zero filter, chaotic
# - parent: warm, respectful    | sibling: banter-heavy, affectionate
# - romantic: intimate          | colleague: friendly but measured
# - boss: polite, professional  | stranger: polite, slightly formal

# You MUST respond with valid JSON only. No markdown, no preamble.
# Schema:
# {{
#   "expressive_text": "<reply using emotion tags>",
#   "detected_mood": "<one word: dominant emotion in the INPUT>",
#   "reasoning": "<one sentence: why you chose this tone>"
# }}
# """.format(emotion_tags=", ".join(EMOTION_TAGS))


# class LLMService:
#     """
#     Groq-hosted Llama - tone detection + expressive Hinglish generation.

#     On init, checks for a user profile and builds a personalised system prompt.
#     Call reload_profile() if profile changes at runtime (e.g. after onboarding).
#     """

#     def __init__(self):
#         settings = get_settings()
#         self._client = AsyncGroq(api_key=settings.groq_api_key)
#         self._model = settings.groq_llm_model
#         self._build_config()

#     def _build_config(self):
#         """Build the system prompt from user profile (or fallback)."""
#         profile = user_profile_store.get()

#         if profile:
#             personality_traits = profile.personality.to_dict()
#             traits_text = "\n".join(
#                 f"- {key}: {value}" for key, value in personality_traits.items()
#             )
#             custom_vibe = profile.custom_vibe.strip() or "none"
#             self._system_prompt = (
#                 f"{profile.llm_system_prompt}\n\n"
#                 "EXTRACTED PERSONALITY TRAITS (always use these when replying):\n"
#                 f"{traits_text}\n"
#                 f"- custom_vibe: {custom_vibe}\n"
#                 f"- voice_gender: {profile.voice_gender}"
#             )
#             self._profile_name = profile.name
#             self._personality_traits = personality_traits
#             self._custom_vibe = profile.custom_vibe.strip()
#         else:
#             self._system_prompt = FALLBACK_SYSTEM_PROMPT
#             self._profile_name = None
#             self._personality_traits = None
#             self._custom_vibe = ""

#     def reload_profile(self):
#         """Call this after onboarding completes to pick up the new profile."""
#         self._build_config()

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------

#     async def generate(
#         self,
#         transcript: str,
#         relationship: Relationship,
#         speaker_name: Optional[str] = None,
#         mood_override: Optional[str] = None,
#         extra_text: Optional[str] = None,
#     ) -> LLMResult:
#         """
#         Generate an expressive Hinglish reply.

#         Args:
#             transcript:    STT output — what the user said.
#             relationship:  Context for tone calibration.
#             speaker_name:  Identified speaker name, if known.
#             mood_override: Force a specific emotion in the reply.
#             extra_text:    Optional extra instruction.

#         Returns:
#             LLMResult with expressive_text, detected_mood, reasoning.
#         """
#         prompt = self._build_prompt(
#             transcript, relationship, speaker_name, mood_override, extra_text
#         )

#         response = await self._client.chat.completions.create(
#             model=self._model,
#             messages=[
#                 {"role": "system", "content": self._system_prompt},
#                 {"role": "user", "content": prompt},
#             ],
#             temperature=0.85,
#             max_tokens=512,
#             response_format={"type": "json_object"},
#         )

#         content = response.choices[0].message.content
#         return self._parse_response(content or "")

#     # ------------------------------------------------------------------
#     # Internal
#     # ------------------------------------------------------------------

#     def _build_prompt(
#         self,
#         transcript: str,
#         relationship: Relationship,
#         speaker_name: Optional[str],
#         mood_override: Optional[str],
#         extra_text: Optional[str],
#     ) -> str:
#         """
#         Per-call context injected into every message.
#         Includes profile name if available so the LLM knows who it's replying for.
#         """
#         lines = [
#             f'Message: "{transcript}"',
#             f"Relationship: {relationship.value}",
#         ]
#         if speaker_name:
#             lines.append(f"Identified speaker name: {speaker_name}")

#         # Per-call personality reinforcement from profile
#         if self._profile_name:
#             lines.append(
#                 f"Replying as {self._profile_name}'s voice assistant - stay true to their personality profile."
#             )
#         if self._personality_traits:
#             traits = ", ".join(
#                 f"{key}={value}" for key, value in self._personality_traits.items()
#             )
#             lines.append(f"Extracted personality traits: {traits}")
#         if self._custom_vibe:
#             lines.append(f"Custom vibe refinement: {self._custom_vibe}")

#         if mood_override and mood_override != "auto":
#             lines.append(
#                 f"Mood override: Reply MUST use the '{mood_override}' emotion tag predominantly."
#             )
#         if extra_text:
#             lines.append(f"Extra instruction: {extra_text}")

#         return "\n".join(lines)

#     @staticmethod
#     def _parse_response(raw: str) -> LLMResult:
#         clean = raw.strip()
#         if clean.startswith("```"):
#             clean = clean.split("\n", 1)[-1]
#             clean = clean.rsplit("```", 1)[0].strip()
#         try:
#             data = json.loads(clean)
#         except json.JSONDecodeError as e:
#             raise ValueError(f"Groq Llama returned non-JSON: {raw!r}") from e
#         return LLMResult(
#             expressive_text=data["expressive_text"],
#             detected_mood=data["detected_mood"],
#             reasoning=data.get("reasoning", ""),
#         )


# # Singleton
# _llm_service: Optional[LLMService] = None


# def get_llm_service() -> LLMService:
#     global _llm_service
#     if _llm_service is None:
#         _llm_service = LLMService()
#     return _llm_service

"""
llm/service.py - Groq Llama LLM for Awaaz v2

If a user profile exists (onboarding completed):
  - System prompt = profile.llm_system_prompt  (personality-tuned, built once at init)
  - Per-call context adds only: relationship, speaker name, mood override, extra text
  - Personality traits are NOT re-injected per call — they're already in the system prompt
>>>>>>> feature/update

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

<<<<<<< HEAD
EMOTION_TAGS = [
    "laughing", "shocked", "whispering", "sad", "angry",
    "scared", "sarcastic", "happy", "neutral", "excited",
]

# ─── Fallback system prompt (used when no onboarding profile exists) ──────────

FALLBACK_SYSTEM_PROMPT = """You are an expressive text generator for a voice assistant.
=======
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
>>>>>>> feature/update

# ─── Emotion tagger system prompt ────────────────────────────────────────────

<<<<<<< HEAD
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
=======
EMOTION_TAGGER_PROMPT = """You are an emotion delivery enhancer for a Silk mulberry Text-to-Speech system.

Your ONLY job: Insert Mulberry inline tags into the user's EXACT text to add expressive delivery.

STRICT RULES:
1. NEVER rewrite, rephrase, expand, or shorten the user's text.
2. NEVER change vocabulary, sentence structure, or word order.
3. Preserve EVERY word from the original text exactly as given.
4. ONLY insert inline tags — they trigger sounds/expressions in TTS, they are not words.

Available inline tags (use the <tag> format): {tags}

Tagging rules:
- Drop a tag anywhere a natural sound or expression would occur
- Tags go at the moment of expression: "seriously? <gasp> I can't believe this"
- Use 1–3 tags maximum — too many sounds unnatural
- Tags are sounds, not labels — <laugh> actually makes it laugh, <sigh> makes it sigh

Mood handling:
- If mood_override is "auto": infer the best tags from the text's natural tone
- If mood_override is specified: prefer tags that match that mood
- Set emotion_source to "auto", "selected", or "combined" accordingly
>>>>>>> feature/update

You MUST respond with valid JSON only. No markdown, no preamble.
Schema:
{{
<<<<<<< HEAD
  "expressive_text": "<reply using emotion tags>",
  "detected_mood": "<one word: dominant emotion in the INPUT>",
  "reasoning": "<one sentence: why you chose this tone>"
}}
""".format(emotion_tags=", ".join(EMOTION_TAGS))
=======
  "expressive_text": "<original text with <inline_tags> inserted at expression moments>",
  "detected_mood": "<primary emotion of the text — one of: happy, sad, excited, calm, confident, empathetic, professional, sarcastic, angry, neutral, whispering, laughing, shocked, scared>",
  "emotion_source": "<auto|selected|combined>",
  "reasoning": "<short phrase: e.g. Auto-inferred: calm or Using selected mood: confident>"
}}""".format(tags=", ".join(f"<{t}>" for t in MULBERRY_INLINE_TAGS))
>>>>>>> feature/update


class LLMService:
    """
<<<<<<< HEAD
    Gemini 2.0 Flash — tone detection + expressive Hinglish generation.

    On init, checks for a user profile and builds a personalised system prompt.
=======
    Groq-hosted Llama — tone detection + expressive Hinglish generation.

    On init, checks for a user profile and builds a personalised system prompt.
    The system prompt carries the full personality — per-call prompts only add
    call-specific context (relationship, speaker, mood override).

>>>>>>> feature/update
    Call reload_profile() if profile changes at runtime (e.g. after onboarding).
    """

    def __init__(self):
        settings = get_settings()
<<<<<<< HEAD
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
=======
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model  = settings.groq_llm_model
        self._build_config()

    def _build_config(self):
        """Build the system prompt from user profile (or fallback)."""
        profile = user_profile_store.get()

        if profile:
            self._system_prompt = profile.llm_system_prompt
            self._profile_name  = profile.name
        else:
            self._system_prompt = EMOTION_TAGGER_PROMPT
            self._profile_name  = None

    def reload_profile(self):
        """Call this after onboarding completes to pick up the new profile."""
        self._build_config()
>>>>>>> feature/update

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
<<<<<<< HEAD
=======
            speaker_name:  Identified speaker name, if known.
>>>>>>> feature/update
            mood_override: Force a specific emotion in the reply.
            extra_text:    Optional extra instruction.

        Returns:
            LLMResult with expressive_text, detected_mood, reasoning.
        """
<<<<<<< HEAD
        prompt = self._build_prompt(transcript, relationship, mood_override, extra_text)
        loop   = asyncio.get_running_loop()

        response = await loop.run_in_executor(
            None,
            lambda: self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=self._config,
            ),
=======
        prompt = self._build_prompt(
            transcript, relationship, speaker_name, mood_override, extra_text
>>>>>>> feature/update
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
<<<<<<< HEAD
        """
        Per-call context injected into every message.
        Includes profile name if available so the LLM knows who it's replying for.
        """
=======
        mood = mood_override or "auto"
>>>>>>> feature/update
        lines = [
            f'Text to tag: "{transcript}"',
            f"mood_override: {mood}",
        ]

<<<<<<< HEAD
        # Per-call personality reinforcement from profile
        if self._profile_name:
            lines.append(f"Replying as {self._profile_name}'s voice assistant — stay true to their personality profile.")

        if mood_override and mood_override != "auto":
            lines.append(
                f"Mood override: Reply MUST use the '{mood_override}' emotion tag predominantly."
            )
        if extra_text:
            lines.append(f"Extra instruction: {extra_text}")
=======
        # Give the LLM concrete tag suggestions for the selected mood
        hints = MOOD_TAG_HINTS.get(mood, [])
        if hints:
            lines.append(f"Suggested tags for this mood: {', '.join(f'<{t}>' for t in hints)}")

        if speaker_name:
            lines.append(f"Speaker: {speaker_name}")

        if extra_text:
            lines.append(f"Context hint: {extra_text}")
>>>>>>> feature/update

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
<<<<<<< HEAD
            raise ValueError(f"Gemini returned non-JSON: {raw!r}") from e
=======
            raise ValueError(f"Groq Llama returned non-JSON: {raw!r}") from e
>>>>>>> feature/update
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