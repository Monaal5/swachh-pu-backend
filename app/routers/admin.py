"""
Admin router — Endpoints for managing user verification requests.
"""

from typing import List
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user, require_role
from app.models.auth import PendingUserResponse, AdminUserDecisionRequest
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin Verification"])


@router.get("/pending-users", response_model=List[PendingUserResponse], dependencies=[Depends(require_role("admin"))])
async def get_pending_users():
    """List all registration applications (students, faculty, workers) pending admin verification."""
    return await admin_service.get_pending_users()


@router.get("/pending-workers", response_model=List[PendingUserResponse], dependencies=[Depends(require_role("admin"))])
async def get_pending_workers():
    """Backward compatibility endpoint to list pending worker registration applications."""
    return await admin_service.get_pending_workers()


@router.post("/users/{profile_id}/verify", dependencies=[Depends(require_role("admin"))])
async def verify_user(
    profile_id: str,
    decision: AdminUserDecisionRequest,
    current_admin: dict = Depends(get_current_user),
):
    """Approve or reject any user application (student, faculty, worker)."""
    return await admin_service.decide_user_verification(
        profile_id=profile_id,
        action=decision.action,
        admin_user_id=str(current_admin["id"]),
        rejection_reason=decision.rejection_reason,
    )




