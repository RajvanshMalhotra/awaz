# Awaaz Latency Optimizations

Tracking every optimization made to reduce end-to-end latency.

**Journey: 46 seconds → 7 seconds** (first audio chunk < 3s via streaming)

### Summary

| Stage | Latency | What changed |
|-------|---------|--------------|
| Baseline | ~46s | Sequential pipeline, lazy speaker load, per-request TTS client, full LLM generation |
| After #1–#3 | ~13s | Speaker pre-warm, persistent TTS client, Whisper turbo |
| After #4–#5 | ~8s | LLM output capped, LLM role → tagger only |
| After #6–#7 | ~5s | Concurrent STT + speaker ID, LLM fires before speaker ID finishes |
| After #8 | ~5s | Mulberry native tags replace fake format (accuracy improvement) |
| After #9 | ~5s | Single-shot pipeline, approve step removed |
| After #10–#11 | ~7s total / <3s first audio | WebSocket streaming, speaker recognition removed |
| After #12 (current) | ~7s total / <3s first audio | Sarvam Saaras v3 codemix STT (better Hinglish accuracy) |

---

## Baseline

**~46 seconds** end-to-end on first real request. Root causes:
- Speaker model (SpeechBrain ECAPA-TDNN, ~80MB) lazy-loaded on first request — full model download + load blocking the pipeline
- TTS created a new `httpx.AsyncClient` per request — full TLS handshake every call (~400ms)
- LLM `max_tokens=512`, temperature `0.85` — long, verbose outputs; slow inference + slow TTS synthesis
- STT: Groq `whisper-large-v3` (full model, slower than turbo variant)
- LLM role: full Hinglish content generation — heavier task, more tokens
- Pipeline: sequential STT → speaker ID → LLM → TTS → user approves → TTS again (two round trips)
- No concurrent execution — each stage waited for the previous to fully complete

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

### 9. Single-shot pipeline — removed approve step
**Files:** `api/pipeline.py`, `frontend.html`  
**Change:** Collapsed the process→approve→TTS two-round-trip flow into a single `POST /pipeline/voice` endpoint. Audio in, TTS audio URL out in one call. Frontend auto-plays on response.  
**Saving:** Eliminates one full network round-trip + user interaction wait  
**Result:** ~5s end-to-end

### 10. WebSocket streaming — LLM→TTS→browser pipeline
**Files:** `api/ws.py`, `tts/service.py` (`synthesize_stream()`), `frontend/src/hooks/useVoiceWS.ts`  
**Change:** Replaced HTTP polling with a persistent WebSocket. TTS `synthesize_stream()` yields audio chunks as they arrive from the Silk API. Server pushes each chunk over the WebSocket immediately. Browser (`useVoiceWS`) queues and plays chunks progressively via Web Audio API.  
**Saving:** User hears first audio chunk in <3s; full response still ~7s but perceived latency is much lower  
**Result:** First audio < 3s, max measured ~7s

### 11. Removed speaker recognition
**Files:** `api/ws.py`, `api/pipeline.py`  
**Change:** Speaker ID (SpeechBrain ECAPA-TDNN) removed from the WebSocket pipeline entirely — not used for LLM input and was adding ~300–500ms to every request.  
**Saving:** ~300–500ms off the critical path

### 12. Switched STT to Sarvam Saaras v3 codemix
**File:** `stt/service.py`  
**Change:** Replaced Groq Whisper with Sarvam `saaras:v3` in codemix mode, which is purpose-built for Hinglish (Roman-script mixed Hindi/English). Sarvam is still in use today.  
**Saving:** Better accuracy on Hinglish speech → fewer retries; comparable speed to Whisper turbo

---

## Current Architecture Critical Path (2026-05-27)

```
Audio in (WebSocket)
  └── STT (Sarvam Saaras v3 codemix)
        └── LLM (Groq Llama 3.3 70B, streaming)
              └── TTS chunks (Silk Mulberry, synthesize_stream)
                    └── WebSocket push → browser Web Audio playback (progressive)
```

**Max measured:** ~7s end-to-end | **First audio chunk:** <3s

---

## v3 Backend Architecture (2026-06-30)

### Dual-Pipeline Architecture

**Ambient path** (always listening):
- Pipecat pipeline: Audio input → VAD → Sarvam STT → Context store (max 5 utterances)
- Context accumulated for reference by sign classifier

**Sign path** (on-demand):
- ISL hand-gesture landmarks (21 points per frame, 64-frame sequences)
- ISL INCLUDE classifier (or rule-based fallback if model unavailable)
- LLM expansion using accumulated context: expand classified sign + ambient context into Hinglish
- TTS synthesis and progressive streaming over WebSocket

**Session isolation:** Both paths share `session_id`; ambient context flows into sign expansion via context store.

### New Components
- **ISL Classifier** (`sign/service.py`): Hand-gesture ISL recognition via ONNX model or fallback rule-based
- **LLM Sign Expansion** (`llm/service.py.generate_sign_expansion()`): Produces Hinglish utterances from ISL+context, streams via Groq
- **Context Store** (`core/context_store.py`): In-memory TTL store, max 5 ambient utterances per session
- **Pipecat Ambient Pipeline** (`api/ambient.py`): VAD + STT chain with context accumulation
- **Sign WebSocket Endpoint** (`api/sign.py`): Landmark input → ISL classify → LLM expand → TTS stream

**Latency:** First sign audio chunk projected <3s (on-par with ambient path).

---

## Remaining Opportunities

| Opportunity | Estimated saving | Complexity |
|---|---|---|
| Browser-side VAD to trim silence before upload | ~100–300ms | Medium |
| Parallel LLM chunk → TTS (don't wait for full sentence) | ~500ms perceived | High |
| Cache Sarvam HTTP client (already persistent) | already done | — |
| Sarvam streaming STT (if available) | ~500ms–1s | Medium |
| ONNX ISL model download at startup (pre-warm) | ~1–2s on first sign request | Low |
| Frontend barge-in detection during audio playback | interrupts existing response | Medium (frontend-driven) |
