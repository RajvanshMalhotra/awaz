import logging

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from core.context_store import get_context_store
from pipecat_pipeline.sarvam_stt import SarvamSTTProcessor

logger = logging.getLogger(__name__)


class ContextAccumulator(FrameProcessor):
    """Intercepts TranscriptionFrames and stores them in the context store."""

    def __init__(self, session_id: str, **kwargs):
        super().__init__(**kwargs)
        self._session_id = session_id

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame) and frame.text.strip():
            get_context_store().append(self._session_id, frame.text)
            logger.debug("[ctx] %s → %r", self._session_id, frame.text)
        await self.push_frame(frame, direction)


async def run_ambient_pipeline(transport, session_id: str) -> None:
    """Build and run the ambient listening pipeline for one WebSocket session.

    `transport` must be a FastAPIWebsocketTransport instance.
    Audio flows: transport.input() → VADProcessor → SarvamSTTProcessor → ContextAccumulator → transport.output()
    """
    vad = VADProcessor(vad_analyzer=SileroVADAnalyzer())
    stt = SarvamSTTProcessor()
    ctx = ContextAccumulator(session_id=session_id)

    pipeline = Pipeline([
        transport.input(),
        vad,
        stt,
        ctx,
        transport.output(),
    ])

    task = PipelineTask(pipeline)
    runner = PipelineRunner()
    await runner.run(task)
