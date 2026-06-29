"""
Admin Service — Handles application verification workflows for students, faculty, and workers.
"""

from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from app.models.auth import PendingUserResponse
from app.utils.supabase_client import get_supabase_admin


async def get_pending_users() -> List[PendingUserResponse]:
    """Fetch all registration requests pending admin verification across students, faculty, and workers."""
    admin = get_supabase_admin()
    results = []

    # 1. Fetch pending student profiles
    sp_res = admin.table("student_profiles").select("*").eq("verification_status", "pending").execute()
    for sp in sp_res.data:
        u_res = admin.table("users").select("*").eq("id", sp["user_id"]).execute()
        if u_res.data:
            u = u_res.data[0]
            results.append(PendingUserResponse(
                profile_id=sp["id"],
                user_id=sp["user_id"],
                name=u["name"],
                email=u["email"],
                role="student",
                phone=u.get("phone"),
                id_card_image=None,
                verification_status=sp["verification_status"],
                created_at=sp["created_at"],
                details={"roll_no": sp.get("roll_no")},
            ))

    # 2. Fetch pending faculty profiles
    fp_res = admin.table("faculty_profiles").select("*").eq("verification_status", "pending").execute()
    for fp in fp_res.data:
        u_res = admin.table("users").select("*").eq("id", fp["user_id"]).execute()
        if u_res.data:
            u = u_res.data[0]
            results.append(PendingUserResponse(
                profile_id=fp["id"],
                user_id=fp["user_id"],
                name=u["name"],
                email=u["email"],
                role="faculty",
                phone=u.get("phone"),
                id_card_image=fp.get("id_card_image", ""),
                verification_status=fp["verification_status"],
                created_at=fp["created_at"],
                details={"faculty_id": fp.get("faculty_id"), "faculty_type": fp.get("faculty_type")},
            ))

    # 3. Fetch pending worker profiles
    wp_res = admin.table("worker_profiles").select("*").eq("verification_status", "pending").execute()
    for wp in wp_res.data:
        u_res = admin.table("users").select("*").eq("id", wp["user_id"]).execute()
        mw_res = admin.table("master_workers").select("*").eq("id", wp["master_worker_id"]).execute()
        if u_res.data and mw_res.data:
            u = u_res.data[0]
            mw = mw_res.data[0]
            results.append(PendingUserResponse(
                profile_id=wp["id"],
                user_id=wp["user_id"],
                name=u["name"],
                email=u["email"],
                role="worker",
                phone=u.get("phone"),
                id_card_image=wp.get("id_card_image", ""),
                verification_status=wp["verification_status"],
                created_at=wp["created_at"],
                details={
                    "worker_id": mw.get("worker_id"),
                    "department": mw.get("department"),
                    "designation": mw.get("designation"),
                },
            ))

    return results


async def get_pending_workers() -> List[PendingUserResponse]:
    """Backward compatibility wrapper."""
    return await get_pending_users()


async def decide_user_verification(
    profile_id: str,
    action: str,
    admin_user_id: str,
    rejection_reason: str = None
) -> dict:
    """Approve or reject a user application (student, faculty, or worker)."""
    admin = get_supabase_admin()

    target_table = None
    profile = None

    # Check worker_profiles first
    res = admin.table("worker_profiles").select("*").eq("id", profile_id).execute()
    if res.data:
        target_table = "worker_profiles"
        profile = res.data[0]
    else:
        # Check student_profiles
        res = admin.table("student_profiles").select("*").eq("id", profile_id).execute()
        if res.data:
            target_table = "student_profiles"
            profile = res.data[0]
        else:
            # Check faculty_profiles
            res = admin.table("faculty_profiles").select("*").eq("id", profile_id).execute()
            if res.data:
                target_table = "faculty_profiles"
                profile = res.data[0]

    if not profile or not target_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User verification request profile not found.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    if action == "approve":
        update_data = {
            "verification_status": "verified",
            "verified_by": admin_user_id,
            "verified_at": now_iso,
        }
        message = "User account has been approved and verified."
    elif action == "reject":
        update_data = {
            "verification_status": "rejected",
            "verified_by": admin_user_id,
            "verified_at": now_iso,
            "rejection_reason": rejection_reason or "ID card verification failed.",
        }
        message = f"User account rejected: {update_data['rejection_reason']}"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve' or 'reject'.",
        )

    admin.table(target_table).update(update_data).eq("id", profile_id).execute()

    return {"status": "success", "message": message}


async def decide_worker_verification(
    worker_profile_id: str,
    action: str,
    admin_user_id: str,
    rejection_reason: str = None
) -> dict:
    """Backward compatibility wrapper."""
    return await decide_user_verification(
        profile_id=worker_profile_id,
        action=action,
        admin_user_id=admin_user_id,
        rejection_reason=rejection_reason,
    )

