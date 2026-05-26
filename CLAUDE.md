# CLAUDE.md


Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

**NOTE**
Keep documenting the optimizations we are doing to reduce latency and the growth we have made.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run onboarding (builds user_profile.json — must do before first pipeline run)
python onboarding_cli.py

# Start the API server
uvicorn main:app --reload --port 8000

# Interactive API docs
# GET http://localhost:8000/docs

# Built-in browser UI
# GET http://localhost:8000/ui

# Standalone test (no FastAPI needed — enroll voices, run speaker ID + LLM)
python test_voice.py

# Full pipeline integration test (requires server running)
python test_pipeline.py
```

## Architecture

Awaaz v2 is a voice-to-expressive-text-to-TTS pipeline for Hinglish conversations.

**Request flow:**
1. `POST /pipeline/process` — audio file in, runs STT and speaker ID concurrently (`asyncio.gather`), then calls LLM, stores state in session store, returns session_id
2. `POST /pipeline/approve` — user approves LLM text, TTS synthesizes it, session consumed
3. `POST /pipeline/deny` — regenerates LLM response with optional overrides, returns new session_id
4. `POST /pipeline/save-speaker` — saves voice profile from audio bytes stored in session

**Session store** (`core/session_store.py`): in-memory, TTL=10min, background purge every 5min. Bridges the process→approve/deny cycle; audio bytes are kept in the session so save-speaker works after the user hears the response.

**User profile** (`core/user_profile.py`, `user_profile.json`): Created by `onboarding_cli.py`. Holds personality dimensions (energy, filter, style, tone, lang_lean) and generates two derived strings at save time:
- `llm_system_prompt` — injected into LLM service at init (not per-call)
- `mulberry_description` — base voice description; emotion suffix is appended per-call in `tts/service.py`

**LLM service** (`llm/service.py`): Groq Llama 3.3 70B Versatile. System prompt is built once at `LLMService.__init__()` from the profile. Call `reload_profile()` if the profile changes at runtime. Falls back to `FALLBACK_SYSTEM_PROMPT` if no profile exists.

**TTS service** (`tts/service.py`): Silk mulberry API (`https://silk-api.rumik.ai/v1/tts`). Speaker resolves from: explicit arg → gender arg → user profile → `SILK_DEFAULT_SPEAKER` env var → `speaker_1`. LLM output in `(emotion)Text...` format is parsed — dominant emotion extracted, all tags stripped for clean TTS text, and emotion suffix appended to the voice description.

**Speaker service** (`speaker/service.py`): SpeechBrain ECAPA-TDNN (`speechbrain/spkrec-ecapa-voxceleb`). Downloads ~80MB model on first run, cached to `pretrained_models/`. Cosine similarity threshold configured via `SPEAKER_SIMILARITY_THRESHOLD` env var (default 0.82). Speaker fingerprints persisted in `voice_store/speakers.json`.

**STT service** (`stt/service.py`): Groq Whisper Large v3, async, returns transcript + detected language.

## Key files

| File | Role |
|------|------|
| `core/models.py` | Single source of truth for all API schemas — check here first |
| `core/config.py` | All env config via pydantic-settings; `get_settings()` is lru_cached |
| `core/user_profile.py` | Profile dataclasses + prompt/description generators |
| `api/pipeline.py` | All route handlers |
| `onboarding_cli.py` | CLI that runs 10-question personality quiz → saves `user_profile.json` |

## Environment variables

Copy `.env.example` to `.env`:

```
GROQ_API_KEY=...
SILK_API_KEY=...                    # Silk mulberry TTS (rumik.ai)
GROQ_LLM_MODEL=llama-3.3-70b-versatile
SILK_DEFAULT_SPEAKER=speaker_1      # speaker_1/2=female, speaker_3/4=male
SILK_DEFAULT_F0_UP_KEY=0
SPEAKER_SIMILARITY_THRESHOLD=0.82
VOICE_STORE_PATH=voice_store/speakers.json
VOICE_AUDIO_DIR=voice_store/audio
USER_PROFILE_PATH=user_profile.json
```

## Important notes

- Many source files contain large blocks of commented-out old code above the active implementation — the active code starts after the final comment block.
- LLM output format: `(emotion)Text...(emotion)Text...` — emotion tags from a fixed set: `laughing, shocked, whispering, sad, angry, scared, sarcastic, happy, neutral, excited`
- `LLMResult.detected_mood` is `str` not the `Mood` enum — LLM occasionally returns values outside the enum.
- `pretrained_models/` and `voice_store/` are gitignored; they are auto-created at runtime.
- Session store is in-memory — restart loses all sessions (by design for hackathon).
- LLM always replies in Roman-script Hinglish regardless of input language — no Devanagari (TTS compatibility constraint).
