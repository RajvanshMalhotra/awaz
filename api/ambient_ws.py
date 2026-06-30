import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pipecat.frames.frames import Frame, InputAudioRawFrame
from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from pipecat_pipeline.ambient_pipeline import run_ambient_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

_SAMPLE_RATE = 16000
_CHANNELS = 1


class RawPCMSerializer(FrameSerializer):
    """Deserializes raw Int16 PCM bytes from WebSocket into InputAudioRawFrame.
    Serialization (output) returns None since this endpoint sends nothing back.
    """

    async def deserialize(self, data: str | bytes) -> Frame | None:
        if isinstance(data, bytes) and data:
            return InputAudioRawFrame(
                audio=data,
                sample_rate=_SAMPLE_RATE,
                num_channels=_CHANNELS,
            )
        return None

    async def serialize(self, frame: Frame) -> str | bytes | None:
        return None


@router.websocket("/ws/ambient")
async def ambient_ws(websocket: WebSocket, session_id: str = "default"):
    """Ambient microphone pipeline.

    Client sends raw PCM audio (Int16, 16 kHz, mono) as binary frames.
    Server accumulates speech context into the ContextStore keyed by session_id.
    No audio is returned to the client.
    """
    await websocket.accept()
    try:
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=False,
                audio_in_sample_rate=_SAMPLE_RATE,
                audio_in_channels=_CHANNELS,
                # Disable origin check for local dev; set PIPECAT_ALLOWED_ORIGINS in prod
                allowed_origins=[],
                serializer=RawPCMSerializer(),
            ),
        )

        await run_ambient_pipeline(transport, session_id=session_id)

    except WebSocketDisconnect:
        logger.info("[ambient] %s disconnected", session_id)
    except Exception as exc:
        logger.exception("[ambient] error for session %s: %s", session_id, exc)
