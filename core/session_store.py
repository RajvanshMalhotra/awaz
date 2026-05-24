import uuid
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

from core.models import ProcessRequest, LLMResult, SpeakerRecognitionResult


@dataclass
class PipelineSession:
    session_id: str
    transcript: str
    detected_language: str
    speaker: SpeakerRecognitionResult
    original_request: ProcessRequest
    llm_result: LLMResult
    audio_bytes: bytes                  # kept for speaker save flow
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.created_at + timedelta(minutes=10)


class SessionStore:
    """
    Simple in-memory store for pipeline sessions.
    Sessions expire after 10 minutes.
    At hackathon scale this is fine; swap for Redis if needed.
    """

    def __init__(self):
        self._store: dict[str, PipelineSession] = {}

    def create(
        self,
        transcript: str,
        detected_language: str,
        speaker: SpeakerRecognitionResult,
        original_request: ProcessRequest,
        llm_result: LLMResult,
        audio_bytes: bytes,
    ) -> PipelineSession:
        session_id = str(uuid.uuid4())
        session = PipelineSession(
            session_id=session_id,
            transcript=transcript,
            detected_language=detected_language,
            speaker=speaker,
            original_request=original_request,
            llm_result=llm_result,
            audio_bytes=audio_bytes,
        )
        self._store[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[PipelineSession]:
        session = self._store.get(session_id)
        if session is None:
            return None
        if session.is_expired():
            del self._store[session_id]
            return None
        return session

    def update_llm(self, session_id: str, llm_result: LLMResult) -> Optional[PipelineSession]:
        """Called on deny-regen to update the LLM result in place."""
        session = self.get(session_id)
        if session is None:
            return None
        session.llm_result = llm_result
        return session

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def purge_expired(self) -> int:
        expired = [sid for sid, s in self._store.items() if s.is_expired()]
        for sid in expired:
            del self._store[sid]
        return len(expired)


# Singleton — imported by routers
session_store = SessionStore()