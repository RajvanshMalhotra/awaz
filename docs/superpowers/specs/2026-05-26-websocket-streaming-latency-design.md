# WebSocket Streaming Latency Optimization — Design Spec

**Date:** 2026-05-26  
**Goal:** Reduce perceived end-to-end latency from ~4.5s to ~1.6s for the voice pipeline.  
**Target:** ≤5s total, ~1.6s to first audio byte.

---

## Problem

`/pipeline/voice` is fully sequential:

```
STT → await → LLM → await → TTS → await → return full WAV
```

Three blocking hops in series. Estimated: STT ~600ms + LLM ~800ms + TTS ~3s = ~4.5s minimum, with variance pushing past 5s.

---

## Solution

Replace `/pipeline/voice` with a WebSocket endpoint `/ws/voice`. Results are pushed to the client as each stage completes. TTS audio is streamed in chunks so playback starts ~200ms into synthesis — before synthesis is done.

---

## Architecture

```
Client                          Server
  |                               |
  |-- binary: audio bytes ------> |
  |                               | STT (Groq Whisper large-v3-turbo)
  | <-- JSON: {transcript} ------ |
  |                               | LLM (Groq Llama 3.3 70B)
  | <-- JSON: {llm result} ------- |
  |                               | TTS stream (Silk mulberry)
  | <-- JSON: {audio_start} ----- |
  | <-- binary: PCM chunk 1 ----- |  ← audio starts here
  | <-- binary: PCM chunk 2 ----- |
  | <-- binary: PCM chunk N ----- |
  | <-- JSON: {audio_end} ------- |
```

**Perceived latency:** STT ~600ms + LLM ~800ms + TTS first chunk ~200ms = **~1.6s** to first audio.

---

## Files Changed

| File | Change |
|------|--------|
| `stt/service.py` | Remove Sarvam path entirely. Always Groq `whisper-large-v3-turbo`. |
| `core/config.py` | Remove `sarvam_api_key` field. |
| `tts/service.py` | Add `synthesize_stream()` async generator yielding raw PCM chunks. |
| `api/ws.py` | New file. WebSocket endpoint `/ws/voice`. |
| `main.py` | Mount WS router. |
| `frontend/` | WebSocket client + Web Audio API queue-based PCM playback. |

---

## Message Protocol

### Server → Client

All text frames are JSON. Binary frames are raw PCM audio chunks.

```json
{"type": "transcript", "text": "...", "language": "hi"}
{"type": "llm", "expressive_text": "...", "detected_mood": "...", "reasoning": "..."}
{"type": "audio_start"}
<binary: raw PCM chunk, 24kHz mono Int16 (WAV PCM after header stripped)>
<binary: ...>
{"type": "audio_end"}
{"type": "error", "message": "..."}
```

### Client → Server

One binary message: the raw audio bytes from `MediaRecorder`. Connection closes after `audio_end` or `error`.

---

## TTS Streaming Detail

Silk mulberry returns WAV (24kHz mono). WAV header encodes total file size — unknown during streaming. 

**Approach:** Strip the 44-byte WAV header on the first chunk server-side, stream raw PCM bytes thereafter. Client interprets all binary frames as 24kHz mono PCM.

```python
async def synthesize_stream(expressive_text, detected_mood) -> AsyncGenerator[bytes, None]:
    async with _get_http_client().stream("POST", SILK_TTS_URL, ...) as response:
        first = True
        async for chunk in response.aiter_bytes(chunk_size=8192):
            if first:
                chunk = chunk[44:]  # strip WAV header
                first = False
            if chunk:
                yield chunk
```

---

## STT Simplification

Remove the Sarvam conditional. `STTService.__init__` becomes:

```python
def __init__(self):
    from groq import AsyncGroq
    self._client = AsyncGroq(api_key=get_settings().groq_api_key)
```

Model: `whisper-large-v3-turbo` hardcoded. Remove `SARVAM_API_KEY` from config and `.env.example`.

---

## Frontend Playback

**Queue-based `AudioBufferSourceNode` chain** for gapless streaming:

1. On `audio_start`: create `AudioContext` (24kHz sample rate), init `nextStartTime = audioCtx.currentTime + 0.1`
2. On binary message: interpret bytes as Int16 PCM → convert to Float32 → create `AudioBuffer` → schedule `AudioBufferSourceNode` at `nextStartTime`, advance `nextStartTime += buffer.duration`
3. On `audio_end`: clean up, re-enable record button
4. On `error` or unexpected close: show error, re-enable record button

**Connection lifecycle:** WebSocket opens per-request, closes after `audio_end`. No reconnection needed.

---

## Error Handling

- STT/LLM/TTS failure → send `{type: "error", message: "..."}` and close WebSocket
- Client on error: display message, re-enable record button
- WebSocket closes unexpectedly: same as error

---

## What This Does NOT Change

- `/pipeline/process` → `/pipeline/approve` two-step flow (unchanged)
- `/pipeline/process-text`, `/pipeline/speak` (unchanged)
- Session store, speaker ID, LLM service (unchanged)
- Speculative TTS precompute on `/process` (unchanged)
