# End Goal
Awaaz v2 — a voice-to-expressive-text-to-TTS pipeline for a hackathon.
User speaks → speaker is identified → STT transcribes → LLM judges tone + writes expressive Hinglish reply in (emotion)Text...format → user approves or denies → TTS speaks it.

# Current Task
Testing voice enrollment, speaker recognition, and LLM generation via `test_voice.py`.

# Completed Work
- [x] Project structure (FastAPI backend, modular services)
- [x] `core/config.py` — pydantic-settings, single .env source
- [x] `core/models.py` — all request/response schemas (API contract), includes STTResult, excited added to Mood enum
- [x] `core/session_store.py` — in-memory session store with expiry, purge loop
- [x] `stt/service.py` — Groq Whisper Large v3, multilingual, async, torchaudio decode
- [x] `speaker/service.py` — SpeechBrain ECAPA-TDNN (replaced resemblyzer — broken on librosa >= 0.9), cosine similarity, JSON persistence
- [x] `llm/service.py` — Gemini 2.0 Flash via google-genai SDK, tone judge + expressive Hinglish writer in one call, structured JSON output
- [x] `tts/service.py` — clean stub, one-block swap on hackathon day
- [x] `api/pipeline.py` — /process, /approve, /deny, /save-speaker routes
- [x] `main.py` — FastAPI app, CORS, lifespan, health check
- [x] `requirements.txt`, `.env.example`
- [x] `__init__.py` files for each package (core, stt, speaker, llm, tts, api)
- [x] `test_voice.py` — interactive enrollment + recognition + LLM test script (no FastAPI needed)

# Remaining Work
- [ ] Integration test script (curl / pytest) for full FastAPI pipeline
- [ ] Error handling middleware (global exception handler)
- [ ] Rate limiting (slowapi) if needed
- [ ] Swap TTS stub on hackathon day (tts/service.py, ~5 lines)
- [ ] Add VOICE_EMOTION tag format converter if TTS model uses different tags
- [ ] Frontend integration (friend's responsibility)

# Architecture Decisions
1. **FastAPI over Next.js API routes** — speaker ID (SpeechBrain) is Python; no reason to add a Python sidecar
2. **STT + Speaker ID run concurrently** — asyncio.gather() in /process, saves ~300ms
3. **Single LLM call** — tone detection + expressive writing in one Gemini call; avoids latency of chaining
4. **Session store** — holds pipeline state (transcript, audio, speaker, llm result) between /process and /approve or /deny. TTL=10min, background purge every 5min
5. **Audio bytes kept in session** — needed for /save-speaker flow (user confirms after hearing the response)
6. **TTS stub pattern** — build_tts_payload() is the adapter; swap just that function on hackathon day
7. **Speaker similarity threshold 0.82** — tunable via env var; lower for noisier environments
8. **Hinglish replies** — LLM always replies in Roman-script Hinglish regardless of input language; no Devanagari (TTS compatibility)
9. **asyncio.get_running_loop()** — used throughout instead of deprecated get_event_loop()

# Tech Stack
| Layer | Library | Notes |
|-------|---------|-------|
| STT | Groq Whisper Large v3 | ~300-600ms, multilingual, verbose_json for language detection |
| Speaker ID | SpeechBrain ECAPA-TDNN | speechbrain/spkrec-ecapa-voxceleb, 192-d embeddings, ~80MB model cached to pretrained_models/ |
| LLM | Gemini 2.0 Flash | google-genai SDK (not google-generativeai), 15 req/min free tier |
| TTS | Stub | swap on hackathon day |
| Audio decode | torchaudio | replaces soundfile+librosa for speaker service |
| API | FastAPI | async, pydantic v2 |

# Important Files
| File | Role |
|------|------|
| `main.py` | FastAPI entrypoint, CORS, lifespan |
| `core/models.py` | ALL API schemas — single source of truth |
| `core/session_store.py` | Pipeline state between process/approve/deny |
| `core/config.py` | All env config via pydantic-settings |
| `stt/service.py` | Groq Whisper v3 transcription |
| `speaker/service.py` | SpeechBrain ECAPA-TDNN speaker fingerprinting |
| `llm/service.py` | Gemini 2.0 Flash — tone + expressive Hinglish text |
| `tts/service.py` | TTS stub — swap on hackathon day |
| `api/pipeline.py` | All route handlers |
| `test_voice.py` | Standalone test: enroll 2 voices → recognize → LLM generate |

# APIs / Contracts

## POST /pipeline/process
Form data: audio (file), relationship, mood_override, extra_text, speaker_name_if_new
Response: { transcript, detected_language, speaker, save_voice_prompt, effective_relationship, relationship_source, llm: { expressive_text, detected_mood, reasoning }, session_id }

## POST /pipeline/approve
Body: { session_id }
Response: { tts_audio_url, tts_payload, expressive_text }

## POST /pipeline/deny
Body: { session_id, mood_override?, relationship_override?, extra_text? }
Response: { llm: { expressive_text, detected_mood, reasoning }, session_id }

## POST /pipeline/save-speaker
Form data: session_id, name
Response: { speaker_id, name, relationship, message }

## LLM Output Format
(laughing)Hahaha...Thatsofunny... (shocked)Wait...Ohmygod...Areyouserious?

## Emotion Tags
laughing, shocked, whispering, sad, angry, scared, sarcastic, happy, neutral, excited

# Models Schema (core/models.py)

## Enums
- Mood: auto, happy, sad, shocked, sarcastic, angry, scared, laughing, whispering, neutral, excited
- Relationship: friend, best_friend, parent, sibling, romantic, colleague, boss, stranger

## Key Models
- STTResult: transcript, detected_language
- SpeakerProfile: speaker_id, name, relationship, embedding (list[float] 192-d), created_at
- SpeakerRecognitionResult: speaker_id, name, relationship, similarity, is_new_speaker
- LLMResult: expressive_text, detected_mood (str), reasoning
- ProcessResponse: transcript, detected_language, speaker, save_voice_prompt, effective_relationship, relationship_source, llm, session_id

# Known Issues / Notes
- SpeechBrain downloads ~80MB model on first run → cached to `pretrained_models/` (add to .gitignore)
- Gemini free tier: 15 req/min Flash — sufficient for hackathon demo
- Session store is in-memory — restart loses sessions (fine for hackathon)
- google-generativeai (old SDK) replaced by google-genai (new SDK) — import is `from google import genai`
- LLMResult.detected_mood is str not Mood enum — LLM occasionally returns values outside enum

# Environment Variables (.env)
```
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
SPEAKER_SIMILARITY_THRESHOLD=0.82
VOICE_STORE_PATH=voice_store/speakers.json
VOICE_AUDIO_DIR=voice_store/audio
```

# .gitignore additions needed
```
.env
pretrained_models/
voice_store/
__pycache__/
*.pyc
```

# Next Recommended Step
1. Run `test_voice.py` — enroll 2 voices, verify recognition + LLM output
2. Once test passes, boot FastAPI: `uvicorn main:app --reload --port 8000`
3. Hit `GET /docs` for interactive API docs
4. Hand off frontend contract to friend

# Repo Structure
awaaz/
├── main.py
├── requirements.txt
├── .env
├── .env.example
├── test_voice.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   └── session_store.py
├── stt/
│   ├── __init__.py
│   └── service.py              # Groq Whisper Large v3
├── speaker/
│   ├── __init__.py
│   └── service.py              # SpeechBrain ECAPA-TDNN
├── llm/
│   ├── __init__.py
│   └── service.py              # Gemini 2.0 Flash (google-genai SDK)
├── tts/
│   ├── __init__.py
│   └── service.py              # stub
├── api/
│   ├── __init__.py
│   └── pipeline.py
├── pretrained_models/          # auto-created, gitignored
│   └── spkrec-ecapa-voxceleb/
└── voice_store/                # auto-created, gitignored
    ├── speakers.json
    └── audio/