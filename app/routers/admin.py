"""
Admin router — Endpoints for managing worker verification requests.
"""

from typing import List
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user, require_role
from app.models.auth import PendingWorkerResponse, AdminWorkerDecisionRequest
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin Verification"])


@router.get("/pending-workers", response_model=List[PendingWorkerResponse], dependencies=[Depends(require_role("admin"))])
async def get_pending_workers():
    """List all worker registration applications pending admin verification."""
    return await admin_service.get_pending_workers()


@router.post("/workers/{worker_profile_id}/verify", dependencies=[Depends(require_role("admin"))])
async def verify_worker(
    worker_profile_id: str,
    decision: AdminWorkerDecisionRequest,
    current_admin: dict = Depends(get_current_user),
):
    """Approve or reject a worker application."""
    return await admin_service.decide_worker_verification(
        worker_profile_id=worker_profile_id,
        action=decision.action,
        admin_user_id=str(current_admin["id"]),
        rejection_reason=decision.rejection_reason,
    )
