# WebSocket Streaming Latency Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the sequential `/pipeline/voice` HTTP endpoint with a bidirectional `/ws/voice` WebSocket that streams transcript, LLM result, and TTS audio progressively, reducing perceived latency from ~4.5s to ~1.6s.

**Architecture:** Client sends audio binary over WebSocket; server pushes transcript after STT, LLM result after generation, then streams raw PCM chunks from Silk TTS as they arrive. Frontend uses Web Audio API queue to play chunks gaplessly as they stream in.

**Tech Stack:** FastAPI WebSocket, httpx async streaming, Groq Whisper + Llama 3.3 70B, Silk mulberry TTS, React/TypeScript, Web Audio API.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `core/config.py` | Remove `sarvam_api_key` field |
| Modify | `stt/service.py` | Remove Sarvam path, always Groq `whisper-large-v3-turbo` |
| Modify | `tts/service.py` | Add `synthesize_stream()` async generator |
| Create | `api/ws.py` | `/ws/voice` WebSocket endpoint |
| Modify | `main.py` | Mount WS router |
| Create | `frontend/src/hooks/useVoiceWS.ts` | WebSocket + Web Audio API hook |
| Modify | `frontend/src/pages/Main.tsx` | Use `useVoiceWS` instead of `api.voice()` |

---

## Task 1: Remove Sarvam from STT and config

**Files:**
- Modify: `core/config.py`
- Modify: `stt/service.py`

- [ ] **Step 1: Remove `sarvam_api_key` from config**

Replace the entire `Settings` class body in `core/config.py` — remove the `sarvam_api_key` field (line 7). The `extra = "ignore"` in `Config` means the env var can still exist in `.env` without breaking anything.

```python
class Settings(BaseSettings):
    groq_api_key: str
    silk_api_key: str
    silk_default_speaker: str = "speaker_1"
    silk_default_f0_up_key: int = 0
    user_profile_path: str = "user_profile.json"
    voice_store_path: str = "voice_store/speakers.json"
    voice_audio_dir: str = "voice_store/audio"
    speaker_similarity_threshold: float = 0.82
    groq_llm_model: str = "llama-3.3-70b-versatile"
    tts_endpoint: str = "http://localhost:9000/synthesize"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
```

- [ ] **Step 2: Rewrite `stt/service.py` to always use Groq**

Replace the entire file content:

```python
import io
import logging
from typing import Optional

from groq import AsyncGroq

from core.config import get_settings
from core.models import STTResult

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self):
        self._client = AsyncGroq(api_key=get_settings().groq_api_key)
        logger.info("STT: Groq whisper-large-v3-turbo")

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
    ) -> STTResult:
        audio_file = (filename, io.BytesIO(audio_bytes), self._infer_mime(filename))
        kwargs: dict = {
            "file": audio_file,
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
        }
        if language:
            kwargs["language"] = language
        response = await self._client.audio.transcriptions.create(**kwargs)
        return STTResult(
            transcript=response.text.strip(),
            detected_language=getattr(response, "language", None),
        )

    @staticmethod
    def _infer_mime(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower()
        return {
            "webm": "audio/webm",
            "wav":  "audio/wav",
            "mp3":  "audio/mpeg",
            "m4a":  "audio/mp4",
            "ogg":  "audio/ogg",
            "flac": "audio/flac",
        }.get(ext, "audio/webm")


_stt_service: Optional[STTService] = None


def get_stt_service() -> STTService:
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService()
    return _stt_service
```

- [ ] **Step 3: Verify STT service starts without Sarvam**

```bash
cd /Users/rajvanshmalhotra/awazv2
python -c "from stt.service import get_stt_service; s = get_stt_service(); print('STT OK')"
```

Expected: `STT: Groq whisper-large-v3-turbo` then `STT OK`

- [ ] **Step 4: Commit**

```bash
git add core/config.py stt/service.py
git commit -m "feat: remove Sarvam STT — always use Groq whisper-large-v3-turbo"
```

---

## Task 2: Add streaming TTS to `tts/service.py`

**Files:**
- Modify: `tts/service.py`

- [ ] **Step 1: Add imports at top of `tts/service.py`**

Add `AsyncGenerator` to the existing imports. The `from __future__ import annotations` is already at the top. Add `AsyncGenerator` to the `typing` import:

```python
from typing import AsyncGenerator, Optional
```

- [ ] **Step 2: Add `synthesize_stream()` function after the `synthesize()` function (after line 135)**

Insert this function between `synthesize()` and `generate_tts_response()`:

```python
async def synthesize_stream(
    expressive_text: str,
    detected_mood: str = "neutral",
) -> AsyncGenerator[bytes, None]:
    """Stream raw PCM chunks from Silk mulberry (WAV header stripped)."""
    api_key = getattr(settings, "silk_api_key", None)
    if not api_key:
        raise RuntimeError("SILK_API_KEY is not set in .env")

    payload = build_tts_payload(expressive_text, detected_mood)
    client = _get_http_client()

    async with client.stream(
        "POST",
        SILK_TTS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    ) as response:
        response.raise_for_status()
        first = True
        async for chunk in response.aiter_bytes(chunk_size=4096):
            if first:
                chunk = chunk[44:]  # strip standard 44-byte WAV header
                first = False
            if chunk:
                yield chunk
```

- [ ] **Step 3: Verify the function is importable**

```bash
python -c "from tts.service import synthesize_stream; print('TTS stream OK')"
```

Expected: `TTS stream OK`

- [ ] **Step 4: Commit**

```bash
git add tts/service.py
git commit -m "feat: add synthesize_stream() async generator to TTS service"
```

---

## Task 3: Create `api/ws.py` — WebSocket endpoint

**Files:**
- Create: `api/ws.py`

- [ ] **Step 1: Create `api/ws.py` with the `/ws/voice` endpoint**

```python
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.models import Relationship
from llm.service import get_llm_service
from stt.service import get_stt_service
from tts.service import synthesize_stream

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket, mood_override: str = "auto"):
    """
    Bidirectional WebSocket voice pipeline.

    Client → Server: one binary message containing raw audio bytes.
    Server → Client:
      {type: "transcript", text, language}     — after STT
      {type: "llm", expressive_text, detected_mood, reasoning}  — after LLM
      {type: "audio_start"}                    — TTS synthesis beginning
      <binary frames: raw Int16 PCM at 24kHz mono>
      {type: "audio_end"}                      — synthesis complete
      {type: "error", message}                 — on any failure
    """
    await websocket.accept()
    try:
        audio_bytes = await websocket.receive_bytes()

        # STT
        stt = get_stt_service()
        transcript_result = await stt.transcribe(audio_bytes, "recording.webm")
        await websocket.send_text(json.dumps({
            "type": "transcript",
            "text": transcript_result.transcript,
            "language": transcript_result.detected_language,
        }))

        # LLM
        llm = get_llm_service()
        llm_result = await llm.generate(
            transcript=transcript_result.transcript,
            relationship=Relationship.friend,
            mood_override=mood_override,
        )
        await websocket.send_text(json.dumps({
            "type": "llm",
            "expressive_text": llm_result.expressive_text,
            "detected_mood": llm_result.detected_mood,
            "reasoning": llm_result.reasoning,
        }))

        # TTS — stream PCM chunks
        await websocket.send_text(json.dumps({"type": "audio_start"}))
        async for chunk in synthesize_stream(llm_result.expressive_text, llm_result.detected_mood):
            await websocket.send_bytes(chunk)
        await websocket.send_text(json.dumps({"type": "audio_end"}))

    except WebSocketDisconnect:
        logger.info("WS /ws/voice: client disconnected")
    except Exception as exc:
        logger.exception("WS /ws/voice error: %s", exc)
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
```

- [ ] **Step 2: Verify the file is importable**

```bash
python -c "from api.ws import router; print('WS router OK')"
```

Expected: `WS router OK`

- [ ] **Step 3: Commit**

```bash
git add api/ws.py
git commit -m "feat: add /ws/voice WebSocket endpoint"
```

---

## Task 4: Mount WS router in `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add the import and router include to `main.py`**

Add the import after the existing `from api.pipeline import router as pipeline_router` line:

```python
from api.ws import router as ws_router
```

Add the router include after `app.include_router(pipeline_router)`:

```python
app.include_router(ws_router)
```

- [ ] **Step 2: Start the server and verify the WebSocket route exists**

```bash
uvicorn main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/openapi.json | python -c "import sys,json; paths=json.load(sys.stdin)['paths']; print('WS routes:', [p for p in paths if 'ws' in p.lower()])"
kill %1
```

Expected output includes `/ws/voice` in the paths list. (FastAPI lists WS routes in openapi.json.)

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: mount WebSocket router in main.py"
```

---

## Task 5: Create `useVoiceWS` hook

**Files:**
- Create: `frontend/src/hooks/useVoiceWS.ts`

- [ ] **Step 1: Create `frontend/src/hooks/useVoiceWS.ts`**

```typescript
import { useCallback, useRef, useState } from 'react'

export interface VoiceWSState {
  transcript: string | null
  expressiveText: string | null
  detectedMood: string | null
  reasoning: string | null
  isProcessing: boolean
  isPlayingAudio: boolean
  error: string | null
}

const INITIAL_STATE: VoiceWSState = {
  transcript: null,
  expressiveText: null,
  detectedMood: null,
  reasoning: null,
  isProcessing: false,
  isPlayingAudio: false,
  error: null,
}

export function useVoiceWS() {
  const [state, setState] = useState<VoiceWSState>(INITIAL_STATE)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const nextStartTimeRef = useRef(0)
  const wsRef = useRef<WebSocket | null>(null)

  const submit = useCallback((blob: Blob, mood: string) => {
    // Close any previous connection
    wsRef.current?.close()
    if (audioCtxRef.current) {
      audioCtxRef.current.close()
      audioCtxRef.current = null
    }

    setState({ ...INITIAL_STATE, isProcessing: true })

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const moodParam = encodeURIComponent(mood)
    const ws = new WebSocket(
      `${protocol}//${window.location.host}/ws/voice?mood_override=${moodParam}`
    )
    wsRef.current = ws
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      ws.send(blob)
    }

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        const msg: { type: string; [key: string]: string } = JSON.parse(event.data)

        if (msg.type === 'transcript') {
          setState(s => ({ ...s, transcript: msg.text }))

        } else if (msg.type === 'llm') {
          setState(s => ({
            ...s,
            expressiveText: msg.expressive_text,
            detectedMood: msg.detected_mood,
            reasoning: msg.reasoning,
          }))

        } else if (msg.type === 'audio_start') {
          const ctx = new AudioContext({ sampleRate: 24000 })
          audioCtxRef.current = ctx
          nextStartTimeRef.current = ctx.currentTime + 0.1
          setState(s => ({ ...s, isPlayingAudio: true }))

        } else if (msg.type === 'audio_end') {
          setState(s => ({ ...s, isProcessing: false, isPlayingAudio: false }))
          ws.close(1000)

        } else if (msg.type === 'error') {
          setState(s => ({ ...s, isProcessing: false, isPlayingAudio: false, error: msg.message }))
          ws.close()
        }

      } else {
        // Binary: Int16 PCM chunk at 24kHz mono
        const ctx = audioCtxRef.current
        if (!ctx) return

        const int16 = new Int16Array(event.data as ArrayBuffer)
        if (int16.length === 0) return

        const float32 = new Float32Array(int16.length)
        for (let i = 0; i < int16.length; i++) {
          float32[i] = int16[i] / 32768.0
        }

        const buffer = ctx.createBuffer(1, float32.length, 24000)
        buffer.copyToChannel(float32, 0)

        const source = ctx.createBufferSource()
        source.buffer = buffer
        source.connect(ctx.destination)

        const startTime = Math.max(nextStartTimeRef.current, ctx.currentTime)
        source.start(startTime)
        nextStartTimeRef.current = startTime + buffer.duration
      }
    }

    ws.onerror = () => {
      setState(s => ({ ...s, isProcessing: false, isPlayingAudio: false, error: 'Connection failed' }))
    }

    ws.onclose = (event) => {
      // Abnormal close codes (not 1000 = normal)
      if (event.code !== 1000 && event.code !== 1001) {
        setState(s => ({ ...s, isProcessing: false, isPlayingAudio: false }))
      }
    }
  }, [])

  const reset = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    if (audioCtxRef.current) {
      audioCtxRef.current.close()
      audioCtxRef.current = null
    }
    setState(INITIAL_STATE)
  }, [])

  return { state, submit, reset }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/rajvanshmalhotra/awazv2/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to `useVoiceWS.ts`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useVoiceWS.ts
git commit -m "feat: add useVoiceWS hook — WebSocket + Web Audio streaming playback"
```

---

## Task 6: Update `Main.tsx` to use `useVoiceWS`

**Files:**
- Modify: `frontend/src/pages/Main.tsx`

The current `submitAudio` calls `api.voice(blob, mood)` and awaits a `VoiceResponse` with a `tts_audio_url`. With WebSocket streaming, audio plays via Web Audio API and there's no URL — so the `<AudioPlayer>` component is replaced with a status indicator. All other UI (transcript, expressive text, mood chip) remains the same, just populated progressively.

- [ ] **Step 1: Update imports in `Main.tsx`**

Replace:
```typescript
import { api, type VoiceResponse, type Profile } from '@/lib/api'
```

With:
```typescript
import { api, type Profile } from '@/lib/api'
import { useVoiceWS } from '@/hooks/useVoiceWS'
```

Also remove the `AudioPlayer` import since it's no longer used in the voice path:
```typescript
// Remove this line:
import { AudioPlayer } from '@/components/AudioPlayer'
```

- [ ] **Step 2: Add the WebSocket hook and update `submitAudio`**

Add the WebSocket hook below the existing hooks (keep `result`, `processing`, and `setProcessing` — they are still used by the text input path via `submitText`):

```typescript
const voiceWS = useVoiceWS()
```

Replace the entire `submitAudio` callback with:
```typescript
const submitAudio = useCallback((blob: Blob) => {
  if (processingRef.current) return
  processingRef.current = true
  latency.start()
  voiceWS.submit(blob, mood)
}, [mood, latency, voiceWS])
```

Note: `result`, `processing`, `setProcessing`, and `setResult` remain in place — `submitText` still uses them for the text input path (which calls `api.speak()` over HTTP, not WebSocket).

- [ ] **Step 3: Update idle/processing conditions to account for both paths**

The voice path uses `voiceWS.state`; the text path uses `processing`/`result`. Update the AnimatePresence conditions:

- Idle block condition: change `!processing && !result` to `!voiceWS.state.isProcessing && !processing && !voiceWS.state.transcript && !result`
- Processing block condition: change `{processing && (` to `{(voiceWS.state.isProcessing || processing) && (`
- Mic button disabled prop: add `voiceWS.state.isProcessing` — `disabled={voiceWS.state.isProcessing || processing}`

- [ ] **Step 4: Stop the latency timer when transcript arrives**

Add a `useEffect` that stops the latency timer when the transcript first appears:

```typescript
const prevTranscriptRef = useRef<string | null>(null)
if (voiceWS.state.transcript && voiceWS.state.transcript !== prevTranscriptRef.current) {
  prevTranscriptRef.current = voiceWS.state.transcript
  latency.stop()
  processingRef.current = false
}
```

- [ ] **Step 5: Update `handleReset` to call `voiceWS.reset()`**

Replace:
```typescript
const handleReset = useCallback(() => {
  setResult(null)
  recorder.reset()
  latency.reset()
  setTimeout(() => textInputRef.current?.focus(), 50)
}, [recorder, latency])
```

With:
```typescript
const handleReset = useCallback(() => {
  voiceWS.reset()
  setResult(null)           // clear text path result too
  recorder.reset()
  latency.reset()
  prevTranscriptRef.current = null
  setTimeout(() => textInputRef.current?.focus(), 50)
}, [voiceWS, recorder, latency])
```

- [ ] **Step 6: Update the result display section**

The `{!processing && result && ...}` block needs to use `voiceWS.state` instead of `result`. Replace the entire result block:

```tsx
{/* Result */}
{!voiceWS.state.isProcessing && voiceWS.state.transcript && (
  <motion.div
    key="result"
    initial={{ opacity: 0, y: 24 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -16 }}
    transition={{ type: 'spring', stiffness: 360, damping: 30 }}
    className="w-full max-w-lg space-y-3"
  >
    {/* Mood chip */}
    {voiceWS.state.detectedMood && (
      <div className="flex items-center gap-2">
        <span className="text-[10px] bg-indigo-500/15 text-indigo-300 px-2.5 py-1 rounded-full font-mono font-semibold">
          {voiceWS.state.detectedMood}
        </span>
        <span className="text-[10px] text-white/20 italic truncate">{voiceWS.state.reasoning}</span>
      </div>
    )}

    {/* Audio status */}
    <div className="bg-emerald-900/20 border border-emerald-500/20 rounded-2xl p-4">
      <p className="text-[10px] text-emerald-300/50 uppercase tracking-widest mb-2">Voice</p>
      {voiceWS.state.isPlayingAudio ? (
        <div className="flex items-center gap-2 text-emerald-300 text-sm">
          <motion.div
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 0.6, repeat: Infinity }}
            className="w-2 h-2 rounded-full bg-emerald-400"
          />
          Playing…
        </div>
      ) : (
        <p className="text-emerald-300/60 text-sm">Playback complete</p>
      )}
    </div>

    {/* What was heard */}
    <div className="bg-white/4 border border-white/8 rounded-2xl p-4">
      <p className="text-[10px] text-white/25 uppercase tracking-widest mb-2">You said</p>
      <p className="text-white/60 text-sm leading-relaxed">{voiceWS.state.transcript}</p>
    </div>

    {/* Expressive text */}
    {voiceWS.state.expressiveText && (
      <div className="bg-indigo-900/15 border border-indigo-500/20 rounded-2xl p-4">
        <p className="text-[10px] text-indigo-300/40 uppercase tracking-widest mb-2">Spoken as</p>
        <p className="text-white/70 text-sm leading-relaxed font-mono break-words">
          {voiceWS.state.expressiveText}
        </p>
      </div>
    )}

    <button
      onClick={handleReset}
      className="w-full bg-white/6 hover:bg-white/10 active:scale-95 text-white/40 font-semibold py-3 rounded-2xl transition-all text-sm"
    >
      ← Say something else
    </button>
  </motion.div>
)}
```

Also update the `AnimatePresence` idle block condition from `!processing && !result` to:
```tsx
{!voiceWS.state.isProcessing && !voiceWS.state.transcript && (
```

- [ ] **Step 7: Show error toasts from voiceWS**

Add a `useEffect` for error handling after the existing hook declarations:

```typescript
const prevErrorRef = useRef<string | null>(null)
if (voiceWS.state.error && voiceWS.state.error !== prevErrorRef.current) {
  prevErrorRef.current = voiceWS.state.error
  toast(voiceWS.state.error, 'error')
}
```

- [ ] **Step 8: Verify TypeScript compiles cleanly**

```bash
cd /Users/rajvanshmalhotra/awazv2/frontend
npx tsc --noEmit 2>&1
```

Expected: no errors.

- [ ] **Step 9: Build the frontend**

```bash
cd /Users/rajvanshmalhotra/awazv2/frontend
npm run build 2>&1 | tail -10
```

Expected: build succeeds with no errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages/Main.tsx
git commit -m "feat: wire Main.tsx to useVoiceWS — progressive transcript + streaming audio"
```

---

## Task 7: End-to-end verification

- [ ] **Step 1: Start the server**

```bash
cd /Users/rajvanshmalhotra/awazv2
uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: Open the app and run a voice request**

Navigate to `http://localhost:8000`. Tap the mic, say something in Hinglish, tap stop. Observe:
- Transcript appears within ~600ms of stopping (before audio starts)
- Audio begins playing within ~1.6s
- Mood chip and expressive text appear before or alongside first audio chunk
- Total perceived latency (stop recording → first audio) should be ≤2s

- [ ] **Step 3: Check browser console for WebSocket frames**

Open DevTools → Network → WS → `/ws/voice`. Verify:
- First text frame: `{"type":"transcript",...}`
- Second text frame: `{"type":"llm",...}`
- Third text frame: `{"type":"audio_start"}`
- Multiple binary frames (PCM chunks)
- Final text frame: `{"type":"audio_end"}`

- [ ] **Step 4: Verify text input path still works**

Type something in the text box and press Enter. Confirm the `api.speak()` path (unchanged) still works and returns audio.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: WebSocket streaming pipeline — ~1.6s perceived latency"
```
