from fastapi import APIRouter, HTTPException

from core.models import (
    OnboardingRequest,
    OnboardingResponse,
    OnboardingStatusResponse,
)
from core.user_profile import Personality, user_profile_store
from llm.service import get_llm_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _profile_response(profile) -> OnboardingResponse:
    return OnboardingResponse(
        name=profile.name,
        voice_gender=profile.voice_gender,
        personality=profile.personality.to_dict(),
        custom_vibe=profile.custom_vibe,
        llm_system_prompt=profile.llm_system_prompt,
        mulberry_description=profile.mulberry_description,
        silk_speaker=profile.silk_speaker(),
    )


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status():
    profile = user_profile_store.get()
    return OnboardingStatusResponse(
        completed=profile is not None,
        profile=_profile_response(profile) if profile else None,
    )


@router.post("", response_model=OnboardingResponse)
async def save_onboarding(body: OnboardingRequest):
    try:
        profile = user_profile_store.save(
            name=body.name,
            voice_gender=body.voice_gender,
            personality=Personality(**body.personality.model_dump()),
            custom_vibe=body.custom_vibe,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    get_llm_service().reload_profile()
    return _profile_response(profile)


@router.delete("", response_model=OnboardingStatusResponse)
async def clear_onboarding():
    user_profile_store.clear()
    get_llm_service().reload_profile()
    return OnboardingStatusResponse(completed=False, profile=None)
