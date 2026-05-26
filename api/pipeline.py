# import asyncio
# import json
# from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

# from core.models import (
#     ProcessResponse, ApproveRequest, ApproveResponse,
#     DenyRequest, DenyResponse, SaveSpeakerResponse,
#     Mood, Relationship, SpeakerRecognitionResult,
# )
# from core.session_store import session_store
# from stt.service import get_stt_service
# from speaker.service import get_speaker_service
# from llm.service import get_llm_service
# from tts.service import get_tts_service, build_tts_payload

# router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# # ---------------------------------------------------------------------------
# # POST /pipeline/process
# # ---------------------------------------------------------------------------

# @router.post("/process", response_model=ProcessResponse)
# async def process_audio(
#     audio: UploadFile = File(..., description="Audio file from browser MediaRecorder (webm/wav)"),
#     relationship: Relationship = Form(Relationship.friend),
#     mood_override: Mood = Form(Mood.auto),
#     extra_text: str | None = Form(None),
#     speaker_name_if_new: str | None = Form(None),
# ):
#     """
#     Main pipeline endpoint. Accepts audio + context, returns transcript,
#     speaker ID result, and LLM-generated expressive text.

#     Relationship resolution priority:
#     1. Known speaker → use their saved relationship (e.g. mom = parent)
#     2. Frontend sent a non-default relationship → use it
#     3. Default: friend

#     The response includes `effective_relationship` and `relationship_source`
#     so the frontend can show the pre-selected relationship in the UI.
#     """
#     audio_bytes = await audio.read()
#     filename = audio.filename or "audio.webm"

#     stt = get_stt_service()
#     speaker_svc = get_speaker_service()
#     llm = get_llm_service()

#     # Run STT and speaker ID concurrently — they're independent
#     transcript_result, speaker_result = await asyncio.gather(
#         stt.transcribe(audio_bytes, filename),
#         speaker_svc.identify(audio_bytes),
#     )

#     # If user pre-named a new speaker in the same request, auto-save
#     if speaker_result.is_new_speaker and speaker_name_if_new:
#         saved = await speaker_svc.save_speaker(
#             speaker_name_if_new, audio_bytes, relationship
#         )
#         speaker_result = SpeakerRecognitionResult(
#             speaker_id=saved.speaker_id,
#             name=saved.name,
#             relationship=saved.relationship,
#             similarity=1.0,
#             is_new_speaker=False,
#         )

#     # Resolve effective relationship
#     if speaker_result.relationship is not None:
#         # Known speaker — their saved relationship takes priority
#         effective_relationship = speaker_result.relationship
#         relationship_source = "speaker_profile"
#     elif relationship != Relationship.friend:
#         # Frontend explicitly chose a non-default relationship
#         effective_relationship = relationship
#         relationship_source = "frontend_override"
#     else:
#         effective_relationship = Relationship.friend
#         relationship_source = "default"

#     llm_result = await llm.generate(
#         transcript=transcript_result.text,
#         speaker_name=speaker_result.name,
#         relationship=effective_relationship,
#         mood_override=mood_override,
#         extra_text=extra_text,
#     )

#     session = session_store.create(
#         transcript=transcript_result.text,
#         detected_language=transcript_result.language,
#         speaker=speaker_result,
#         original_request=_make_process_request(
#             effective_relationship, mood_override, extra_text, speaker_name_if_new
#         ),
#         llm_result=llm_result,
#         audio_bytes=audio_bytes,
#     )

#     return ProcessResponse(
#         transcript=transcript_result.text,
#         detected_language=transcript_result.language,
#         speaker=speaker_result,
#         save_voice_prompt=speaker_result.is_new_speaker,
#         effective_relationship=effective_relationship,
#         relationship_source=relationship_source,
#         llm=llm_result,
#         session_id=session.session_id,
#     )


# # ---------------------------------------------------------------------------
# # POST /pipeline/approve
# # ---------------------------------------------------------------------------

# @router.post("/approve", response_model=ApproveResponse)
# async def approve(body: ApproveRequest):
#     """
#     User approved the generated text. Forward to TTS.
#     Session is consumed (deleted) after approval.
#     """
#     session = session_store.get(body.session_id)
#     if not session:
#         raise HTTPException(status_code=404, detail="Session not found or expired")

#     tts = get_tts_service()
#     payload = build_tts_payload(session.llm_result, session.speaker.name)
#     tts_response = await tts.synthesize(payload)

#     session_store.delete(body.session_id)

#     return ApproveResponse(
#         tts_audio_url=tts_response.get("audio_url"),
#         tts_payload=payload,
#         expressive_text=session.llm_result.expressive_text,
#     )


# # ---------------------------------------------------------------------------
# # POST /pipeline/deny
# # ---------------------------------------------------------------------------

# @router.post("/deny", response_model=DenyResponse)
# async def deny(body: DenyRequest):
#     """
#     User denied the output. Accepts overrides, regenerates LLM response.
#     Returns new session_id for the next approve/deny cycle.
#     """
#     session = session_store.get(body.session_id)
#     if not session:
#         raise HTTPException(status_code=404, detail="Session not found or expired")

#     orig = session.original_request
#     effective_mood = body.mood_override or orig.mood_override
#     effective_relationship = body.relationship_override or orig.relationship
#     effective_extra = body.extra_text or orig.extra_text

#     llm = get_llm_service()
#     new_llm_result = await llm.generate(
#         transcript=session.transcript,
#         speaker_name=session.speaker.name,
#         relationship=effective_relationship,
#         mood_override=effective_mood,
#         extra_text=effective_extra,
#     )

#     # Create new session with updated result — old one stays until expiry
#     new_session = session_store.create(
#         transcript=session.transcript,
#         detected_language=session.detected_language,
#         speaker=session.speaker,
#         original_request=_make_process_request(
#             effective_relationship, effective_mood, effective_extra, None
#         ),
#         llm_result=new_llm_result,
#         audio_bytes=session.audio_bytes,
#     )

#     return DenyResponse(
#         llm=new_llm_result,
#         session_id=new_session.session_id,
#     )


# # ---------------------------------------------------------------------------
# # POST /pipeline/save-speaker
# # ---------------------------------------------------------------------------

# @router.post("/save-speaker", response_model=SaveSpeakerResponse)
# async def save_speaker(
#     session_id: str = Form(...),
#     name: str = Form(..., min_length=1, max_length=64),
#     relationship: Relationship = Form(Relationship.friend),
# ):
#     """
#     Called when user confirms "Save this voice?".
#     Uses audio stored in the session to create the voice profile.
#     The relationship field permanently links this voice to Mom, Dad, etc.
#     """
#     session = session_store.get(session_id)
#     if not session:
#         raise HTTPException(status_code=404, detail="Session not found or expired")

#     if not session.speaker.is_new_speaker:
#         raise HTTPException(status_code=400, detail="Speaker already identified")

#     speaker_svc = get_speaker_service()
#     profile = await speaker_svc.save_speaker(name, session.audio_bytes, relationship)

#     return SaveSpeakerResponse(
#         speaker_id=profile.speaker_id,
#         name=profile.name,
#         relationship=profile.relationship,
#         message=f"Voice profile saved for {profile.name} ({relationship.value})",
#     )


# # ---------------------------------------------------------------------------
# # Helper
# # ---------------------------------------------------------------------------

# def _make_process_request(relationship, mood_override, extra_text, speaker_name_if_new):
#     from core.models import ProcessRequest
#     return ProcessRequest(
#         relationship=relationship,
#         mood_override=mood_override,
#         extra_text=extra_text,
#         speaker_name_if_new=speaker_name_if_new,
#     )

import asyncio
import logging
import uuid as _uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from core.models import (
    ProcessResponse, ApproveRequest, ApproveResponse,
    DenyRequest, DenyResponse,
    Mood, Relationship,
)
from core.session_store import session_store
from stt.service import get_stt_service
from llm.service import get_llm_service
from tts.service import generate_tts_response
from sign.service import get_sign_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# ---------------------------------------------------------------------------
# POST /pipeline/voice  — single-shot: audio in, TTS audio out (~5s total)
# STT + speaker ID run concurrently, then LLM, then TTS — no session/approve step.
# ---------------------------------------------------------------------------

@router.post("/voice")
async def voice_pipeline(
    audio: UploadFile = File(...),
    mood_override: Mood = Form(Mood.auto),
):
    """
    Single-shot pipeline for mute users:
    voice → STT → LLM (generates expressive response in user's voice) → TTS.
    No speaker identification — always uses the profile's default voice.
    Target latency: ≤5s.
    """
    audio_bytes = await audio.read()
    filename = audio.filename or "audio.webm"

    transcript_result = await get_stt_service().transcribe(audio_bytes, filename)

    llm_result = await get_llm_service().generate(
        transcript=transcript_result.transcript,
        relationship=Relationship.friend,
        mood_override=mood_override.value,
    )

    tts_result = await generate_tts_response(
        expressive_text=llm_result.expressive_text,
        detected_mood=llm_result.detected_mood,
        session_id=str(_uuid.uuid4()),
    )

    return {
        "transcript": transcript_result.transcript,
        "expressive_text": llm_result.expressive_text,
        "detected_mood": llm_result.detected_mood,
        "reasoning": llm_result.reasoning,
        "tts_audio_url": tts_result["tts_audio_url"],
    }


async def _precompute_tts(session_id: str) -> None:
    """
    Fire TTS immediately after /process so it's ready when the user clicks Approve.
    Runs as a background task — failure is logged and silently ignored.
    """
    try:
        session = session_store.get(session_id)
        if not session:
            return
        result = await generate_tts_response(
            expressive_text=session.llm_result.expressive_text,
            detected_mood=session.llm_result.detected_mood,
            session_id=session_id,
        )
        # Re-fetch in case session expired while TTS was running
        session = session_store.get(session_id)
        if session:
            session.tts_result = result
            logger.info("TTS precomputed for session %s", session_id)
    except Exception as exc:
        logger.warning("TTS precompute failed for %s: %s", session_id, exc)


# ---------------------------------------------------------------------------
# POST /pipeline/process
# ---------------------------------------------------------------------------

@router.post("/process", response_model=ProcessResponse)
async def process_audio(
    audio: UploadFile = File(..., description="Audio file from browser MediaRecorder (webm/wav)"),
    relationship: Relationship = Form(Relationship.friend),
    mood_override: Mood = Form(Mood.auto),
    extra_text: str | None = Form(None),
    voice_gender: str | None = Form(None, description="User's onboarding voice choice"),
):
    audio_bytes = await audio.read()
    filename = audio.filename or "audio.webm"

    transcript_result = await get_stt_service().transcribe(audio_bytes, filename)

    llm_result = await get_llm_service().generate(
        transcript=transcript_result.transcript,
        relationship=relationship,
        mood_override=mood_override,
        extra_text=extra_text,
    )

    effective_relationship = relationship
    relationship_source = "frontend_override" if relationship != Relationship.friend else "default"

    session = session_store.create(
        transcript=transcript_result.transcript,
        detected_language=transcript_result.detected_language,
        original_request=_make_process_request(effective_relationship, mood_override, extra_text),
        llm_result=llm_result,
        audio_bytes=audio_bytes,
        voice_gender=voice_gender,
    )

    asyncio.create_task(_precompute_tts(session.session_id))

    return ProcessResponse(
        transcript=transcript_result.transcript,
        detected_language=transcript_result.detected_language,
        effective_relationship=effective_relationship,
        relationship_source=relationship_source,
        llm=llm_result,
        session_id=session.session_id,
    )


# ---------------------------------------------------------------------------
# POST /pipeline/process-text  — keyboard / sign-language text input
# Skips STT and speaker ID entirely: text → LLM → TTS (speculative)
# Typical latency: ~1-2 s vs ~6-10 s for the audio path
# ---------------------------------------------------------------------------

@router.post("/process-text", response_model=ProcessResponse)
async def process_text(
    text: str = Form(...),
    relationship: Relationship = Form(Relationship.friend),
    mood_override: Mood = Form(Mood.auto),
    extra_text: str | None = Form(None),
):
    llm_result = await get_llm_service().generate(
        transcript=text,
        relationship=relationship,
        mood_override=mood_override,
        extra_text=extra_text,
        mode="express",
    )

    session = session_store.create(
        transcript=text,
        detected_language=None,
        original_request=_make_process_request(relationship, mood_override, extra_text),
        llm_result=llm_result,
        audio_bytes=b"",
    )

    asyncio.create_task(_precompute_tts(session.session_id))

    return ProcessResponse(
        transcript=text,
        detected_language=None,
        effective_relationship=relationship,
        relationship_source="frontend_override",
        llm=llm_result,
        session_id=session.session_id,
    )


# ---------------------------------------------------------------------------
# POST /pipeline/speak  — single-shot text input (no STT, no speaker ID)
# text → LLM → TTS, returns audio URL directly. Mirrors /pipeline/voice.
# ---------------------------------------------------------------------------

@router.post("/speak")
async def speak_pipeline(
    text: str = Form(...),
    mood_override: Mood = Form(Mood.auto),
):
    """
    Text-input equivalent of /pipeline/voice.
    Skips STT. LLM generates an expressive response, TTS synthesizes it.
    Target latency: ≤3s.
    """
    llm_result = await get_llm_service().generate(
        transcript=text,
        relationship=Relationship.friend,
        mood_override=mood_override.value,
        mode="express",
    )

    tts_result = await generate_tts_response(
        expressive_text=llm_result.expressive_text,
        detected_mood=llm_result.detected_mood,
        session_id=str(_uuid.uuid4()),
    )

    return {
        "transcript": text,
        "expressive_text": llm_result.expressive_text,
        "detected_mood": llm_result.detected_mood,
        "reasoning": llm_result.reasoning,
        "tts_audio_url": tts_result["tts_audio_url"],
    }


# ---------------------------------------------------------------------------
# POST /pipeline/approve
# ---------------------------------------------------------------------------

@router.post("/approve", response_model=ApproveResponse)
async def approve(body: ApproveRequest):
    """
    User approved the generated text. Synthesize via Silk mulberry TTS.
    Session is consumed (deleted) after approval.

    voice_gender stored in session during /process is used automatically.
    Frontend can also pass it explicitly in the body if the user changes
    their voice preference mid-session (rare but supported).
    """
    session = session_store.get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if session.tts_result:
        logger.info("Approve: using precomputed TTS for %s", body.session_id)
        tts_result = session.tts_result
    else:
        logger.info("Approve: TTS not ready yet, computing now for %s", body.session_id)
        tts_result = await generate_tts_response(
            expressive_text=session.llm_result.expressive_text,
            detected_mood=session.llm_result.detected_mood,
            session_id=body.session_id,
        )

    session_store.delete(body.session_id)

    return ApproveResponse(
        tts_audio_url=tts_result["tts_audio_url"],
        tts_payload=tts_result["tts_payload"],
        expressive_text=tts_result["expressive_text"],
    )


# ---------------------------------------------------------------------------
# POST /pipeline/deny
# ---------------------------------------------------------------------------

@router.post("/deny", response_model=DenyResponse)
async def deny(body: DenyRequest):
    """
    User denied the output. Accepts overrides, regenerates LLM response.
    Returns a new session_id for the next approve/deny cycle.
    voice_gender is carried forward into the new session automatically.
    """
    session = session_store.get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    orig = session.original_request
    effective_mood         = body.mood_override         or orig.mood_override
    effective_relationship = body.relationship_override or orig.relationship
    effective_extra        = body.extra_text            or orig.extra_text

    new_llm_result = await get_llm_service().generate(
        transcript=session.transcript,
        relationship=effective_relationship,
        mood_override=effective_mood,
        extra_text=effective_extra,
    )

    new_session = session_store.create(
        transcript=session.transcript,
        detected_language=session.detected_language,
        original_request=_make_process_request(effective_relationship, effective_mood, effective_extra),
        llm_result=new_llm_result,
        audio_bytes=session.audio_bytes,
        voice_gender=session.voice_gender,
    )

    # Precompute TTS for the retry session too
    asyncio.create_task(_precompute_tts(new_session.session_id))

    return DenyResponse(
        llm=new_llm_result,
        session_id=new_session.session_id,
    )


# ---------------------------------------------------------------------------
# Sign language
# ---------------------------------------------------------------------------

class SignLanguageRequest(BaseModel):
    landmarks: list[list[list[float]]]  # frames × 21 landmarks × [x, y, z]


class SignLanguageResponse(BaseModel):
    text: str


@router.post("/sign-language", response_model=SignLanguageResponse)
async def sign_language(body: SignLanguageRequest) -> SignLanguageResponse:
    if not body.landmarks:
        raise HTTPException(status_code=422, detail="No landmark frames provided")
    svc = get_sign_service()
    text = await asyncio.to_thread(svc.classify, body.landmarks)
    return SignLanguageResponse(text=text)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_process_request(relationship, mood_override, extra_text):
    from core.models import ProcessRequest
    return ProcessRequest(
        relationship=relationship,
        mood_override=mood_override,
        extra_text=extra_text,
    )
