# Awaaz Latency Optimizations

Tracking every optimization made to reduce end-to-end latency. Goal: **under 5 seconds** from audio input to TTS audio output.

---

## Baseline

**~13 seconds** end-to-end on first request. Root causes identified:
- Speaker model (SpeechBrain ECAPA-TDNN) lazy-loads on first request — `initialize()` existed but was never called at startup
- TTS created a new `httpx.AsyncClient` per request — full TLS handshake every call (~400ms)
- LLM `max_tokens=512` — produced long outputs, slower inference and longer TTS synthesis
- Whisper large-v3 — turbo variant available but not used
- LLM doing content generation (rewriting text in Hinglish) — heavier task than needed

---

## Optimizations Applied

### 1. Speaker model pre-warm at startup
**File:** `main.py` — lifespan function  
**Change:** `await get_speaker_service().initialize()` called at server startup instead of lazy-loading on first request  
**Saving:** ~5–10 seconds on first request (SpeechBrain ECAPA-TDNN model download + load)

### 2. Persistent TTS HTTP client
**File:** `tts/service.py`  
**Change:** Module-level `httpx.AsyncClient` replaces per-request `async with httpx.AsyncClient(...) as client`  
**Saving:** ~400ms per TTS call (eliminates TLS handshake on each request)

### 3. Faster STT model
**File:** `stt/service.py`  
**Change:** `whisper-large-v3` → `whisper-large-v3-turbo`  
**Saving:** ~3x faster transcription on Groq infra (same accuracy for conversational speech)

### 4. LLM output size reduction
**File:** `llm/service.py`  
**Change:** `max_tokens=512` → `max_tokens=200`; temperature `0.85` → `0.7`  
**Saving:** Shorter LLM output = faster inference + shorter text = faster TTS synthesis

### 5. LLM role change: tagger only, not generator
**File:** `llm/service.py`, `core/user_profile.py`  
**Change:** LLM no longer generates Hinglish responses. It only inserts Mulberry-native `<inline_tags>` into the user's exact words.  
**Saving:** Simpler task = fewer output tokens, more deterministic output, shorter TTS text  
**Product benefit:** Preserves user's exact meaning; no hallucinated content

### 8. Mulberry-native inline tags replace fake (emotion) format
**Files:** `llm/service.py`, `tts/service.py`, `core/user_profile.py`, `api/pipeline.py`  
**Change:** The previous `(emotion)Text...` format was invented and Mulberry didn't understand it. The fix:
- LLM now inserts Mulberry's actual `<laugh>`, `<sigh>`, `<gasp>`, `<sarcastic>`, etc. inline tags directly into the text
- TTS sends the tagged text as-is (no stripping/parsing step)
- Voice description uses Mulberry's documented emotion vocabulary (`energetic`, `sad`, `excited`, `sarcastic`, `angry`, etc.)
- `mulberry_description` rebuilt using vd.md attribute vocabulary (accent, pacing, timbre, register)  
**Saving:** Removes an entire text-parsing step; more accurate TTS expressiveness since tags are actually understood by the model

### 6. Concurrent STT + Speaker ID
**File:** `api/pipeline.py`  
**Change:** STT and speaker identification run concurrently via `asyncio.create_task` + `asyncio.gather`  
**Saving:** Speaker ID (~300–500ms) runs in parallel with STT instead of sequentially

### 7. LLM fires before speaker ID completes
**File:** `api/pipeline.py`  
**Change:** LLM task starts as soon as STT transcript is available, while speaker ID task is still running  
**Saving:** Removes speaker ID latency from the critical path when speaker result isn't needed for LLM input

---

## Current Architecture Critical Path

```
Audio in
  └── STT (Groq Whisper turbo) ─────────────────────────┐
  └── Speaker ID (SpeechBrain, pre-warmed) ──────┐       │
                                                  │  LLM fires on transcript ──→ TTS (persistent client) ──→ Audio out
                                          gather  │
                                                  └── Speaker result merged
```

---

## Remaining Opportunities

| Opportunity | Estimated saving | Complexity |
|---|---|---|
| Stream TTS audio (chunked response) | ~1-2s perceived latency | Medium |
| Cache speaker embeddings in memory (avoid disk reads) | ~50ms | Low |
| Reduce speaker similarity threshold check to top-N only | ~20ms | Low |
| Browser-side VAD to trim silence before upload | ~100-300ms | Medium |
| Sign language input (MediaPipe, browser-side) | Eliminates STT entirely for sign | High |
