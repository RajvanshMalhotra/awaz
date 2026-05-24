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
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from core.models import (
    ProcessResponse, ApproveRequest, ApproveResponse,
    DenyRequest, DenyResponse, SaveSpeakerResponse,
    Mood, Relationship, SpeakerRecognitionResult,
)
from core.session_store import session_store
from stt.service import get_stt_service
from speaker.service import get_speaker_service
from llm.service import get_llm_service
from tts.service import generate_tts_response, build_tts_payload

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# ---------------------------------------------------------------------------
# POST /pipeline/process
# ---------------------------------------------------------------------------

@router.post("/process", response_model=ProcessResponse)
async def process_audio(
    audio: UploadFile = File(..., description="Audio file from browser MediaRecorder (webm/wav)"),
    relationship: Relationship = Form(Relationship.friend),
    mood_override: Mood = Form(Mood.auto),
    extra_text: str | None = Form(None),
    speaker_name_if_new: str | None = Form(None),
    # Onboarding voice preference — stored in user profile on the frontend,
    # forwarded here so TTS uses the right speaker from the very first request.
    # Values: "female" | "female_alt" | "male" | "male_deep"
    # or a raw Silk preset: "speaker_1" | "speaker_2" | "speaker_3" | "speaker_4"
    voice_gender: str | None = Form(None, description="User's onboarding voice choice"),
):
    """
    Main pipeline endpoint. Accepts audio + context, returns transcript,
    speaker ID result, and LLM-generated expressive text.

    Relationship resolution priority:
    1. Known speaker → use their saved relationship (e.g. mom = parent)
    2. Frontend sent a non-default relationship → use it
    3. Default: friend

    The response includes `effective_relationship` and `relationship_source`
    so the frontend can show the pre-selected relationship in the UI.
    """
    audio_bytes = await audio.read()
    filename = audio.filename or "audio.webm"

    stt = get_stt_service()
    speaker_svc = get_speaker_service()
    llm = get_llm_service()

    # Run STT and speaker ID concurrently — they're independent
    transcript_result, speaker_result = await asyncio.gather(
        stt.transcribe(audio_bytes, filename),
        speaker_svc.identify(audio_bytes),
    )

    # If user pre-named a new speaker in the same request, auto-save
    if speaker_result.is_new_speaker and speaker_name_if_new:
        saved = await speaker_svc.save_speaker(
            speaker_name_if_new, audio_bytes, relationship
        )
        speaker_result = SpeakerRecognitionResult(
            speaker_id=saved.speaker_id,
            name=saved.name,
            relationship=saved.relationship,
            similarity=1.0,
            is_new_speaker=False,
        )

    # Resolve effective relationship
    if speaker_result.relationship is not None:
        effective_relationship = speaker_result.relationship
        relationship_source = "speaker_profile"
    elif relationship != Relationship.friend:
        effective_relationship = relationship
        relationship_source = "frontend_override"
    else:
        effective_relationship = Relationship.friend
        relationship_source = "default"

    llm_result = await llm.generate(
        transcript=transcript_result.text,
        speaker_name=speaker_result.name,
        relationship=effective_relationship,
        mood_override=mood_override,
        extra_text=extra_text,
    )

    session = session_store.create(
        transcript=transcript_result.text,
        detected_language=transcript_result.language,
        speaker=speaker_result,
        original_request=_make_process_request(
            effective_relationship, mood_override, extra_text, speaker_name_if_new
        ),
        llm_result=llm_result,
        audio_bytes=audio_bytes,
        voice_gender=voice_gender,          # persisted so /approve doesn't need it again
    )

    return ProcessResponse(
        transcript=transcript_result.text,
        detected_language=transcript_result.language,
        speaker=speaker_result,
        save_voice_prompt=speaker_result.is_new_speaker,
        effective_relationship=effective_relationship,
        relationship_source=relationship_source,
        llm=llm_result,
        session_id=session.session_id,
    )


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

    # Prefer explicit override in approve body, fall back to what /process stored
    voice_gender = getattr(body, "voice_gender", None) or getattr(session, "voice_gender", None)

    tts_result = await generate_tts_response(
        expressive_text=session.llm_result.expressive_text,
        session_id=body.session_id,
        gender=voice_gender,        # e.g. "female" / "male" — resolved inside tts.service
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

    llm = get_llm_service()
    new_llm_result = await llm.generate(
        transcript=session.transcript,
        speaker_name=session.speaker.name,
        relationship=effective_relationship,
        mood_override=effective_mood,
        extra_text=effective_extra,
    )

    # Carry voice_gender forward so the next /approve still uses the right voice
    new_session = session_store.create(
        transcript=session.transcript,
        detected_language=session.detected_language,
        speaker=session.speaker,
        original_request=_make_process_request(
            effective_relationship, effective_mood, effective_extra, None
        ),
        llm_result=new_llm_result,
        audio_bytes=session.audio_bytes,
        voice_gender=getattr(session, "voice_gender", None),
    )

    return DenyResponse(
        llm=new_llm_result,
        session_id=new_session.session_id,
    )


# ---------------------------------------------------------------------------
# POST /pipeline/save-speaker
# ---------------------------------------------------------------------------

@router.post("/save-speaker", response_model=SaveSpeakerResponse)
async def save_speaker(
    session_id: str = Form(...),
    name: str = Form(..., min_length=1, max_length=64),
    relationship: Relationship = Form(Relationship.friend),
):
    """
    Called when user confirms "Save this voice?".
    Uses audio stored in the session to create the voice profile.
    The relationship field permanently links this voice to Mom, Dad, etc.
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if not session.speaker.is_new_speaker:
        raise HTTPException(status_code=400, detail="Speaker already identified")

    speaker_svc = get_speaker_service()
    profile = await speaker_svc.save_speaker(name, session.audio_bytes, relationship)

    return SaveSpeakerResponse(
        speaker_id=profile.speaker_id,
        name=profile.name,
        relationship=profile.relationship,
        message=f"Voice profile saved for {profile.name} ({relationship.value})",
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_process_request(relationship, mood_override, extra_text, speaker_name_if_new):
    from core.models import ProcessRequest
    return ProcessRequest(
        relationship=relationship,
        mood_override=mood_override,
        extra_text=extra_text,
        speaker_name_if_new=speaker_name_if_new,
    )