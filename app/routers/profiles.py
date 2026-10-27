"""
Profile router — CRUD operations on user profiles.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, require_role
from app.models.profile import ProfileResponse, ProfileListResponse, UpdateProfileRequest
from app.services import profile_service

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(user: dict = Depends(get_current_user)):
    """Get the current user's full profile (base + student/worker details)."""
    return await profile_service.get_profile_by_id(user["id"])


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    data: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
):
    """Update the current user's profile. Only non-null fields are updated."""
    return await profile_service.update_profile(user, data)


@router.get("/public/list", response_model=ProfileListResponse)
async def list_profiles_public():
    """
    List all profiles without authentication (for testing).
    """
    profiles = await profile_service.list_profiles()
    return ProfileListResponse(profiles=profiles, count=len(profiles))


@router.get("/public/workers", response_model=ProfileListResponse)
async def list_workers_public():
    """
    List all worker profiles without authentication (for testing).
    """
    workers = await profile_service.list_workers()
    return ProfileListResponse(profiles=workers, count=len(workers))


@router.get("/workers", response_model=ProfileListResponse)
async def list_workers(user: dict = Depends(require_role("admin"))):
    """
    List all worker profiles.

    **Admin only** — used to populate the worker dropdown when assigning tasks.
    """
    workers = await profile_service.list_workers()
    return ProfileListResponse(profiles=workers, count=len(workers))


@router.get("/list", response_model=ProfileListResponse)
async def list_profiles_api(user: dict = Depends(get_current_user)):
    """
    List all profiles.

    Accessible by any authenticated user.
    """
    profiles = await profile_service.list_profiles()
    return ProfileListResponse(profiles=profiles, count=len(profiles))


@router.get("/workers/list", response_model=ProfileListResponse)
async def list_workers_authenticated(user: dict = Depends(get_current_user)):
    """
    List all worker profiles.

    Accessible by any authenticated user.
    """
    workers = await profile_service.list_workers()
    return ProfileListResponse(profiles=workers, count=len(workers))


# Declared last so /list and /workers/list are not captured as a profile ID
@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str, user: dict = Depends(require_role("admin"))):
    """
    Get any profile by ID.

    **Admin only**.
    """
    return await profile_service.get_profile_by_id(profile_id)


# Separate top-level router for /workers
workers_router = APIRouter(prefix="/workers", tags=["Workers"])


@workers_router.get("/list", response_model=ProfileListResponse)
async def list_workers_top_level(user: dict = Depends(get_current_user)):
    """
    List all worker profiles.

    Accessible by any authenticated user.
    """
    workers = await profile_service.list_workers()
    return ProfileListResponse(profiles=workers, count=len(workers))

