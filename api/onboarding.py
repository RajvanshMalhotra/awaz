from fastapi import APIRouter, HTTPException

from core.models import (
    OnboardingRequest,
    OnboardingResponse,
    OnboardingStatusResponse,
    ProfileListResponse,
)
from core.user_profile import Personality, user_profile_store
from llm.service import get_llm_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _profile_response(profile) -> OnboardingResponse:
    return OnboardingResponse(
        profile_id=profile.profile_id,
        name=profile.name,
        personality=profile.personality.to_dict(),
        custom_vibe=profile.custom_vibe,
        llm_system_prompt=profile.llm_system_prompt,
        mulberry_description=profile.mulberry_description,
    )


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status():
    profile = user_profile_store.get()
    return OnboardingStatusResponse(
        completed=profile is not None,
        profile=_profile_response(profile) if profile else None,
    )


@router.get("/profiles", response_model=ProfileListResponse)
async def list_profiles():
    return ProfileListResponse(
        active_id=user_profile_store.get_active_id(),
        profiles=[_profile_response(p) for p in user_profile_store.get_all()],
    )


@router.post("", response_model=OnboardingResponse)
async def save_onboarding(body: OnboardingRequest):
    try:
        profile = user_profile_store.save(
            name=body.name,
            personality=Personality(**body.personality.model_dump()),
            custom_vibe=body.custom_vibe,
            profile_id=body.profile_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    get_llm_service().reload_profile()
    return _profile_response(profile)


@router.put("/profiles/{profile_id}/activate", response_model=OnboardingResponse)
async def activate_profile(profile_id: str):
    ok = user_profile_store.activate(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")
    get_llm_service().reload_profile()
    return _profile_response(user_profile_store.get())


@router.delete("/profiles/{profile_id}", response_model=ProfileListResponse)
async def delete_profile(profile_id: str):
    ok = user_profile_store.delete(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")
    get_llm_service().reload_profile()
    return ProfileListResponse(
        active_id=user_profile_store.get_active_id(),
        profiles=[_profile_response(p) for p in user_profile_store.get_all()],
    )


@router.delete("", response_model=OnboardingStatusResponse)
async def clear_onboarding():
    user_profile_store.clear()
    get_llm_service().reload_profile()
    return OnboardingStatusResponse(completed=False, profile=None)
