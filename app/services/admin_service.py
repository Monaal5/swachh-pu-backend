"""
Admin Service — Handles worker application verification workflows.
"""

from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from app.models.auth import PendingWorkerResponse
from app.utils.supabase_client import get_supabase_admin


async def get_pending_workers() -> List[PendingWorkerResponse]:
    """Fetch all worker registration requests pending admin verification."""
    admin = get_supabase_admin()

    try:
        res = (
            admin.table("worker_profiles")
            .select("*, users!inner(id, name, email), master_workers!inner(worker_id, department, designation)")
            .eq("verification_status", "pending")
            .execute()
        )
    except Exception:
        # Fallback query if deep joins need separate fetching
        res = admin.table("worker_profiles").select("*").eq("verification_status", "pending").execute()
        results = []
        for wp in res.data:
            u = admin.table("users").select("*").eq("id", wp["user_id"]).execute().data[0]
            mw = admin.table("master_workers").select("*").eq("id", wp["master_worker_id"]).execute().data[0]
            results.append(PendingWorkerResponse(
                worker_profile_id=wp["id"],
                user_id=wp["user_id"],
                name=u["name"],
                email=u["email"],
                worker_id=mw["worker_id"],
                department=mw["department"],
                designation=mw["designation"],
                id_card_image=wp["id_card_image"],
                verification_status=wp["verification_status"],
                created_at=wp["created_at"],
            ))
        return results

    results = []
    for item in res.data:
        u = item["users"]
        mw = item["master_workers"]
        results.append(PendingWorkerResponse(
            worker_profile_id=item["id"],
            user_id=item["user_id"],
            name=u["name"],
            email=u["email"],
            worker_id=mw["worker_id"],
            department=mw["department"],
            designation=mw["designation"],
            id_card_image=item["id_card_image"],
            verification_status=item["verification_status"],
            created_at=item["created_at"],
        ))
    return results


async def decide_worker_verification(
    worker_profile_id: str,
    action: str,
    admin_user_id: str,
    rejection_reason: str = None
) -> dict:
    """Approve or reject a worker application."""
    admin = get_supabase_admin()

    wp_res = admin.table("worker_profiles").select("*").eq("id", worker_profile_id).execute()
    if not wp_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker profile request not found.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    if action == "approve":
        update_data = {
            "verification_status": "verified",
            "verified_by": admin_user_id,
            "verified_at": now_iso,
        }
        message = "Worker account has been approved and verified."
    elif action == "reject":
        update_data = {
            "verification_status": "rejected",
            "verified_by": admin_user_id,
            "verified_at": now_iso,
            "rejection_reason": rejection_reason or "ID card verification failed.",
        }
        message = f"Worker account rejected: {update_data['rejection_reason']}"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve' or 'reject'.",
        )

    admin.table("worker_profiles").update(update_data).eq("id", worker_profile_id).execute()

    return {"status": "success", "message": message}
