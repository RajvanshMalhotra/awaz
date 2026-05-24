import json
import asyncio
from typing import Optional

from google import genai
from google.genai import types

from core.config import get_settings
from core.models import LLMResult, Relationship


# All valid emotion tags — must stay in sync with TTS service expectations
EMOTION_TAGS = [
    "laughing", "shocked", "whispering", "sad", "angry",
    "scared", "sarcastic", "happy", "neutral", "excited",
]

SYSTEM_PROMPT = """You are an expressive text generator for a voice assistant.

Given a transcribed message, a relationship context, and an optional mood override:
1. Detect the emotional tone of the input message.
2. Write a warm, natural reply that fits the relationship and tone.
3. Format the reply using emotion tags like: (laughing)Hahaha...Thats so funny... (shocked)Wait...Ohmygod...

Language rules (STRICT):
- ALWAYS reply in Hinglish — Roman-script Hindi mixed naturally with English.
- Do NOT use Devanagari script. Every word must be ASCII/Roman only.
- Mix ratio should feel natural, not forced: Hindi words for emotion/warmth/fillers,
  English for clarity. Examples of natural Hinglish:
  "yaar...sunasunasuna...thisistoocrazy..." / "areyaar...Icannotbelievethis..."
  "kya bolrahahai...Ohmygod...seriouslybata"
- Filler words that work well: yaar, arre, bhai, sach mein, matlab, kya, acha, haan, bas
- If the input is already in English, still reply in Hinglish.
- If the input is in Hindi (Devanagari or Roman), reply in Hinglish.

Rules for expressive text format:
- Use emotion tags from this list ONLY: {emotion_tags}
- Tags wrap the words that carry that emotion — switch tags mid-sentence if needed.
- Compress spaces within emotional bursts: "Oh my god" → "Ohmygod", "yaar sun" → "yaarsun"
- Use ellipsis (...) to indicate natural speech pauses and trailing off.
- Keep replies conversational length — not too short, not a paragraph.
- The reply should feel like it comes from a real person, not an assistant.

Relationship affects tone:
- friend: casual, playful, no filter
- best_friend: zero filter, chaotic, deeply comfortable
- parent: warm, respectful, can be gently teasing
- sibling: banter-heavy, affectionate, no formality
- romantic: intimate, affectionate, can be vulnerable
- colleague: friendly but measured
- boss: polite, professional, slight deference
- stranger: polite, slightly formal

You MUST respond with valid JSON only. No markdown, no preamble.
Schema:
{{
  "expressive_text": "<reply using emotion tags>",
  "detected_mood": "<one word: the dominant emotion you detected in the INPUT>",
  "reasoning": "<one sentence: why you chose this tone for the reply>"
}}
""".format(emotion_tags=", ".join(EMOTION_TAGS))


class LLMService:
    """
    Single Gemini 2.0 Flash call that does two jobs:
    1. Judges the emotional tone of the incoming transcript.
    2. Writes an expressive Hinglish reply using (emotion)Text... format for TTS.

    Uses the modern google-genai SDK (google-genai package, not google-generativeai).
    Async-native via asyncio.get_running_loop().run_in_executor for the sync SDK call.

    Gemini free tier: 15 req/min Flash — sufficient for hackathon demo.
    """

    def __init__(self):
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = "gemini-2.0-flash"
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.8,
            max_output_tokens=512,
            response_mime_type="application/json",
        )

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
        Generate an expressive Hinglish reply for a given transcript.

        Args:
            transcript:     STT output — what the user said.
            relationship:   Context for tone calibration.
            mood_override:  Force a specific reply emotion (e.g. "excited").
            extra_text:     Optional extra instruction (e.g. "make it funnier").

        Returns:
            LLMResult with expressive_text, detected_mood, reasoning.
        """
        prompt = self._build_prompt(transcript, relationship, mood_override, extra_text)
        loop = asyncio.get_running_loop()

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
        lines = [
            f'Message: "{transcript}"',
            f"Relationship: {relationship.value}",
        ]
        if mood_override:
            lines.append(
                f"Mood override: Reply MUST use the '{mood_override}' emotion tag predominantly."
            )
        if extra_text:
            lines.append(f"Extra instruction: {extra_text}")
        return "\n".join(lines)

    @staticmethod
    def _parse_response(raw: str) -> LLMResult:
        """Parse Gemini JSON output → LLMResult. Strips markdown fences if present."""
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1]
            clean = clean.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned non-JSON output: {raw!r}") from e

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