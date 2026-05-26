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
