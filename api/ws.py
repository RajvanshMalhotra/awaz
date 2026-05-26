import asyncio
import json
import logging
import re
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.models import Mood, Relationship
from llm.service import get_llm_service
from stt.service import get_stt_service
from tts.service import synthesize_stream

logger = logging.getLogger(__name__)
router = APIRouter()

# Extract fields from a partial or complete JSON token stream
_TEXT_RE   = re.compile(r'"expressive_text"\s*:\s*"((?:[^"\\]|\\.)*)"')
_MOOD_RE   = re.compile(r'"detected_mood"\s*:\s*"([^"]+)"')
_REASON_RE = re.compile(r'"reasoning"\s*:\s*"([^"]+)"')


@router.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket, mood_override: str = "auto"):
    """
    Pipelined WebSocket voice path:

      client audio → STT → LLM stream → TTS (starts as soon as text extracted)
                                       ↕ concurrent
                                 remaining LLM tokens for mood/reasoning

    Message order guaranteed:
      transcript → llm → audio_start → <binary PCM chunks> → audio_end
    """
    await websocket.accept()

    valid_moods = {m.value for m in Mood}
    if mood_override not in valid_moods:
        mood_override = "auto"

    try:
        audio_bytes = await websocket.receive_bytes()
        t_recv = time.perf_counter()

        # ── STT ──────────────────────────────────────────────────────────────
        stt = get_stt_service()
        transcript_result = await stt.transcribe(audio_bytes, "recording.webm")
        logger.info("[ws] STT %.2fs → %r", time.perf_counter() - t_recv, transcript_result.transcript[:60])

        await websocket.send_text(json.dumps({
            "type": "transcript",
            "text": transcript_result.transcript,
            "language": transcript_result.detected_language,
        }))

        # ── LLM stream ───────────────────────────────────────────────────────
        t_llm = time.perf_counter()
        llm = get_llm_service()

        llm_buffer = ""
        expressive_text: str | None = None
        tts_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        tts_task: asyncio.Task | None = None

        async def _run_tts(text: str) -> None:
            try:
                async for chunk in synthesize_stream(text, mood_override):
                    await tts_queue.put(chunk)
            except Exception as exc:
                logger.exception("[ws] TTS error: %s", exc)
            finally:
                await tts_queue.put(None)  # sentinel — always signals done

        # Consume LLM token stream; fire TTS as soon as expressive_text is complete
        async for token in llm.generate_stream(
            transcript=transcript_result.transcript,
            relationship=Relationship.friend,
            mood_override=mood_override,
        ):
            llm_buffer += token
            if expressive_text is None:
                m = _TEXT_RE.search(llm_buffer)
                if m:
                    expressive_text = m.group(1)
                    logger.info("[ws] LLM text ready %.2fs — launching TTS", time.perf_counter() - t_llm)
                    tts_task = asyncio.create_task(_run_tts(expressive_text))

        logger.info("[ws] LLM done %.2fs", time.perf_counter() - t_llm)

        # Fallback: if regex missed (shouldn't happen), parse whole JSON
        if expressive_text is None:
            try:
                parsed = json.loads(llm_buffer)
                expressive_text = parsed.get("expressive_text", "")
            except json.JSONDecodeError:
                expressive_text = llm_buffer.strip()
            logger.warning("[ws] regex miss — fell back to JSON parse")
            tts_task = asyncio.create_task(_run_tts(expressive_text))

        # Extract mood / reasoning from completed buffer
        mood_m   = _MOOD_RE.search(llm_buffer)
        reason_m = _REASON_RE.search(llm_buffer)
        detected_mood = mood_m.group(1)   if mood_m   else "neutral"
        reasoning     = reason_m.group(1) if reason_m else ""

        # Send LLM metadata (TTS is already running concurrently)
        await websocket.send_text(json.dumps({
            "type":            "llm",
            "expressive_text": expressive_text,
            "detected_mood":   detected_mood,
            "reasoning":       reasoning,
        }))

        # Signal client to open AudioContext, start latency measurement end
        await websocket.send_text(json.dumps({"type": "audio_start"}))
        t_tts_first = None

        # Drain TTS queue → forward to client
        while True:
            chunk = await tts_queue.get()
            if chunk is None:
                break
            if t_tts_first is None:
                t_tts_first = time.perf_counter()
                logger.info("[ws] TTS first byte %.2fs after recv", t_tts_first - t_recv)
            await websocket.send_bytes(chunk)

        await websocket.send_text(json.dumps({"type": "audio_end"}))
        logger.info("[ws] total pipeline %.2fs", time.perf_counter() - t_recv)

        if tts_task:
            await tts_task  # ensure any lingering exception surfaces

    except WebSocketDisconnect:
        logger.info("[ws] client disconnected")
    except Exception as exc:
        logger.exception("[ws] error: %s", exc)
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
