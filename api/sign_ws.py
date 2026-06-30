import asyncio
import json
import logging
import re
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.context_store import get_context_store
from llm.service import get_llm_service
from sign.service import get_sign_service
from tts.service import synthesize_stream

logger = logging.getLogger(__name__)
router = APIRouter()

_CONFIDENCE_THRESHOLD = 0.60
_TEXT_RE = re.compile(r'"expressive_text"\s*:\s*"((?:[^"\\]|\\.)*)"')
_MOOD_RE = re.compile(r'"detected_mood"\s*:\s*"([^"]+)"')


@router.websocket("/ws/sign")
async def sign_ws(websocket: WebSocket):
    """Sign language input → LLM expansion → TTS audio stream.

    Client sends JSON messages. Two message types:
      landmarks: ISL landmark sequence to classify and expand
      accepted:  user accepted a phrase; store it for future personalisation

    The vocabulary store path for accepted phrases:
      voice_store/vocabulary_{session_id}.json
    """
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "accepted":
                _store_accepted(
                    session_id=msg.get("session_id", "default"),
                    sign=msg["sign"],
                    phrase=msg["phrase"],
                )
                continue

            if msg.get("type") != "landmarks":
                continue

            t_recv = time.perf_counter()
            frames = msg["frames"]       # list[list[list[float]]]
            session_id = msg.get("session_id", "default")
            mood = msg.get("mood", "auto")

            # ── ISL classification ────────────────────────────────────────
            sign_svc = get_sign_service()
            word, confidence = sign_svc.classify_with_confidence(frames)

            if confidence < _CONFIDENCE_THRESHOLD:
                await websocket.send_text(json.dumps({
                    "type": "sign",
                    "word": word,
                    "confidence": round(confidence, 3),
                    "confident": False,
                }))
                continue

            await websocket.send_text(json.dumps({
                "type": "sign",
                "word": word,
                "confidence": round(confidence, 3),
                "confident": True,
            }))
            logger.info("[sign] %.2fs — %r (%.0f%%)", time.perf_counter() - t_recv, word, confidence * 100)

            # ── LLM expansion ────────────────────────────────────────────
            t_llm = time.perf_counter()
            llm = get_llm_service()
            context = get_context_store().get(session_id)
            accepted = _load_accepted(session_id, word)

            llm_buffer = ""
            expressive_text: str | None = None
            tts_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
            tts_task: asyncio.Task | None = None

            async def _run_tts(text: str) -> None:
                try:
                    async for chunk in synthesize_stream(text, mood):
                        await tts_queue.put(chunk)
                except Exception as exc:
                    logger.exception("[sign] TTS error: %s", exc)
                finally:
                    await tts_queue.put(None)

            async for token in llm.generate_sign_expansion(
                signed_words=[word],
                context=context,
                accepted_phrases=accepted,
                mood_override=mood,
            ):
                llm_buffer += token
                if expressive_text is None:
                    m = _TEXT_RE.search(llm_buffer)
                    if m:
                        expressive_text = m.group(1)
                        logger.info("[sign] LLM text ready %.2fs — launching TTS", time.perf_counter() - t_llm)
                        tts_task = asyncio.create_task(_run_tts(expressive_text))

            if expressive_text is None:
                try:
                    parsed = json.loads(llm_buffer)
                    expressive_text = parsed.get("expressive_text", word)
                except json.JSONDecodeError:
                    expressive_text = word
                tts_task = asyncio.create_task(_run_tts(expressive_text))

            mood_m = _MOOD_RE.search(llm_buffer)
            detected_mood = mood_m.group(1) if mood_m else "neutral"

            await websocket.send_text(json.dumps({
                "type": "llm",
                "expressive_text": expressive_text,
                "detected_mood": detected_mood,
            }))

            await websocket.send_text(json.dumps({"type": "audio_start"}))

            while True:
                chunk = await tts_queue.get()
                if chunk is None:
                    break
                await websocket.send_bytes(chunk)

            await websocket.send_text(json.dumps({"type": "audio_end"}))
            logger.info("[sign] total %.2fs", time.perf_counter() - t_recv)

            if tts_task:
                await tts_task

    except WebSocketDisconnect:
        logger.info("[sign] client disconnected")
    except Exception as exc:
        logger.exception("[sign] error: %s", exc)
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass


# ── Vocabulary helpers ────────────────────────────────────────────────────────

import json as _json
from pathlib import Path

_VOCAB_DIR = Path("voice_store")


def _vocab_path(session_id: str) -> Path:
    _VOCAB_DIR.mkdir(exist_ok=True)
    return _VOCAB_DIR / f"vocabulary_{session_id}.json"


def _load_accepted(session_id: str, sign: str) -> list[str]:
    path = _vocab_path(session_id)
    if not path.exists():
        return []
    try:
        data = _json.loads(path.read_text())
        return data.get(sign, [])[:3]
    except Exception:
        return []


def _store_accepted(session_id: str, sign: str, phrase: str) -> None:
    path = _vocab_path(session_id)
    data: dict[str, list[str]] = {}
    if path.exists():
        try:
            data = _json.loads(path.read_text())
        except Exception:
            data = {}
    phrases = data.get(sign, [])
    if phrase not in phrases:
        phrases.append(phrase)
    data[sign] = phrases[-10:]  # keep last 10 per sign
    path.write_text(_json.dumps(data, ensure_ascii=False, indent=2))
