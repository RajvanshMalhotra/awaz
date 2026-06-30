# Task 4 Report: Pipecat Ambient Pipeline

## Status: DONE

## What was discovered (pre-implementation verification)

### Transport import path
`pipecat.transports.network.fastapi_websocket` does NOT exist in pipecat 1.4.0.
Correct path: `pipecat.transports.websocket.fastapi.FastAPIWebsocketTransport`

### VAD module path
`pipecat.vad.silero` does NOT exist in pipecat 1.4.0.
Correct paths:
- `pipecat.audio.vad.silero.SileroVADAnalyzer` — the analyzer
- `pipecat.processors.audio.vad_processor.VADProcessor` — wraps the analyzer as a FrameProcessor

### VAD frame name
`VADUserStoppedSpeakingFrame` — confirmed present in `pipecat.frames.frames`.

### Serializer requirement
In pipecat 1.4, `FastAPIWebsocketInputTransport._receive_messages()` has `if not self._params.serializer: continue` — without a serializer it silently discards all incoming messages. A `RawPCMSerializer` was written in `api/ambient_ws.py` that converts raw binary WebSocket bytes into `InputAudioRawFrame`.

### Audio frame type
The transport pushes `InputAudioRawFrame` (not `AudioRawFrame`) so `SarvamSTTProcessor` was updated to match.

## Files created

- `pipecat_pipeline/__init__.py` — empty
- `pipecat_pipeline/sarvam_stt.py` — `SarvamSTTProcessor`: buffers `InputAudioRawFrame.audio`, transcribes on `VADUserStoppedSpeakingFrame`, pushes `TranscriptionFrame`
- `pipecat_pipeline/ambient_pipeline.py` — `ContextAccumulator` + `run_ambient_pipeline()` wiring transport → VADProcessor → SarvamSTTProcessor → ContextAccumulator → transport output
- `api/ambient_ws.py` — `RawPCMSerializer` (raw bytes → `InputAudioRawFrame`), `GET /ws/ambient?session_id=<id>` WebSocket endpoint

## Files modified

- `main.py` — added `from api.ambient_ws import router as ambient_ws_router` and `app.include_router(ambient_ws_router)`
- `requirements.txt` — added `pipecat-ai[silero]==1.4.0`

## Pipeline architecture

```
WebSocket binary (Int16 PCM 16kHz mono)
  ↓ RawPCMSerializer.deserialize()
  ↓ FastAPIWebsocketInputTransport
  ↓ VADProcessor(SileroVADAnalyzer)  ← pushes VADUserStoppedSpeakingFrame on silence
  ↓ SarvamSTTProcessor               ← buffers audio, transcribes on VAD stop
  ↓ ContextAccumulator               ← calls context_store.append(session_id, text)
  ↓ FastAPIWebsocketOutputTransport  ← no-op (audio_out_enabled=False)
```

## Tests

All 10 prior tests pass:
```
10 passed, 1 warning in 0.37s
```

## Smoke test output

```
sent silence, no exception
done
```

Server started without error. WebSocket connected, 1 second of silence (32000 bytes Int16 PCM) sent without exception. Pipeline accepted connection and handled the silent audio. No transcription triggered (silence below VAD threshold, as expected).

## Concerns

None. The implementation is straightforward. One note: the `SarvamSTTService.transcribe()` raises `ValueError` if the transcript is too short ("Audio unclear or too short") — `SarvamSTTProcessor._transcribe_and_push()` catches all exceptions and logs them, so short/silent utterances fail gracefully without crashing the pipeline.
