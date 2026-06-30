import asyncio
import logging

from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    TranscriptionFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16000
_CHANNELS = 1


class SarvamSTTProcessor(FrameProcessor):
    """Buffers InputAudioRawFrames; on VAD stop, transcribes with Sarvam and pushes
    a TranscriptionFrame downstream."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._audio_buffer: list[bytes] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, InputAudioRawFrame):
            self._audio_buffer.append(frame.audio)
            # Don't push the raw frame downstream — we consume it here
            return

        if isinstance(frame, VADUserStoppedSpeakingFrame):
            if self._audio_buffer:
                audio_bytes = b"".join(self._audio_buffer)
                self._audio_buffer = []
                self.create_task(self._transcribe_and_push(audio_bytes))
            await self.push_frame(frame, direction)
            return

        await self.push_frame(frame, direction)

    async def _transcribe_and_push(self, audio_bytes: bytes) -> None:
        try:
            from stt.service import get_stt_service
            stt = get_stt_service()
            result = await stt.transcribe(audio_bytes, "ambient.wav")
            if result.transcript.strip():
                logger.debug("[ambient] transcript: %r", result.transcript)
                await self.push_frame(
                    TranscriptionFrame(
                        text=result.transcript,
                        user_id="ambient",
                        timestamp="",
                    )
                )
        except Exception as exc:
            logger.exception("[ambient] STT error: %s", exc)
