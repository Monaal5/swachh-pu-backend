"""
Profile service — Supabase queries for profile CRUD.
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.models.profile import (
    ProfileResponse,
    StudentProfileDetail,
    FacultyProfileDetail,
    WorkerProfileDetail,
    UpdateProfileRequest,
)
from app.utils.supabase_client import get_supabase_admin


def _enrich_worker_dict(worker_prof: dict, master_workers_map: dict) -> dict:
    if not worker_prof:
        return None
    mw_id = str(worker_prof.get("master_worker_id"))
    master = master_workers_map.get(mw_id, {})
    return {
        "employee_id": master.get("worker_id"),
        "zone": worker_prof.get("zone"),
        "id_card_image": worker_prof.get("id_card_image"),
        "verification_status": worker_prof.get("verification_status", "verified"),
        "address": master.get("address"),
        "date_of_joining": master.get("date_of_joining"),
        "department": master.get("department"),
        "status": master.get("status"),
        "designation": master.get("designation"),
    }


def _build_profile_response(profile: dict, student: Optional[dict], faculty: Optional[dict], worker: Optional[dict]) -> ProfileResponse:
    """Helper to assemble a ProfileResponse from raw DB rows."""
    student_detail = None
    faculty_detail = None
    worker_detail = None

    if student:
        student_detail = StudentProfileDetail(
            roll_no=student["roll_no"],
            id_card_image=student.get("id_card_image"),
            verification_status=student.get("verification_status", "pending"),
            address=student.get("address"),
            hostel=student.get("hostel"),
        )

    if faculty:
        faculty_detail = FacultyProfileDetail(
            faculty_id=faculty["faculty_id"],
            faculty_type=faculty["faculty_type"],
            id_card_image=faculty.get("id_card_image"),
            verification_status=faculty.get("verification_status", "pending"),
        )

    if worker:
        worker_detail = WorkerProfileDetail(
            employee_id=worker.get("employee_id"),
            zone=worker.get("zone"),
            id_card_image=worker.get("id_card_image"),
            verification_status=worker.get("verification_status", "pending"),
            address=worker.get("address"),
            date_of_joining=str(worker.get("date_of_joining")) if worker.get("date_of_joining") else None,
            department=worker.get("department"),
            status=worker.get("status"),
            designation=worker.get("designation"),
        )

    return ProfileResponse(
        id=profile["id"],
        user_id=profile["user_id"],
        name=profile["name"],
        role=profile["role"],
        phone=profile.get("phone"),
        created_at=profile["created_at"],
        student_detail=student_detail,
        faculty_detail=faculty_detail,
        worker_detail=worker_detail,
    )


async def get_profile_by_user_id(user_id: str) -> ProfileResponse:
    """Get full profile (base + role-specific) by auth user_id."""
    admin = get_supabase_admin()

    result = admin.table("profiles").select("*").eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    profile = result.data[0]
    return await _enrich_profile(profile)


async def get_profile_by_id(profile_id: str) -> ProfileResponse:
    """Get full profile by profile ID."""
    admin = get_supabase_admin()

    result = admin.table("profiles").select("*").eq("id", profile_id).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    profile = result.data[0]
    return await _enrich_profile(profile)


async def _enrich_profile(profile: dict) -> ProfileResponse:
    """Fetch role-specific data and build full response."""
    admin = get_supabase_admin()
    student = None
    faculty = None
    worker = None

    if profile["role"] == "student":
        sp = admin.table("student_profiles").select("*").eq("user_id", profile["user_id"]).execute()
        student = sp.data[0] if sp.data else None

    elif profile["role"] == "faculty":
        fp = admin.table("faculty_profiles").select("*").eq("user_id", profile["user_id"]).execute()
        faculty = fp.data[0] if fp.data else None

    elif profile["role"] == "worker":
        wp = admin.table("worker_profiles").select("*").eq("user_id", profile["user_id"]).execute()
        if wp.data:
            worker_prof = wp.data[0]
            mw = admin.table("master_workers").select("*").eq("id", worker_prof["master_worker_id"]).execute()
            mw_map = {str(mw.data[0]["id"]): mw.data[0]} if mw.data else {}
            worker = _enrich_worker_dict(worker_prof, mw_map)

    return _build_profile_response(profile, student, faculty, worker)


async def list_profiles() -> list[ProfileResponse]:
    """List all profiles."""
    admin = get_supabase_admin()

    result = admin.table("profiles").select("*, student_profiles(*), faculty_profiles(*), worker_profiles(*)").execute()

    mw_res = admin.table("master_workers").select("*").execute()
    mw_map = {str(mw["id"]): mw for mw in mw_res.data}

    profiles = []
    for p in result.data:
        try:
            student_raw = p.get("student_profiles")
            student = student_raw[0] if isinstance(student_raw, list) and student_raw else (student_raw if isinstance(student_raw, dict) else None)

            faculty_raw = p.get("faculty_profiles")
            faculty = faculty_raw[0] if isinstance(faculty_raw, list) and faculty_raw else (faculty_raw if isinstance(faculty_raw, dict) else None)

            worker_raw = p.get("worker_profiles")
            worker_prof = worker_raw[0] if isinstance(worker_raw, list) and worker_raw else (worker_raw if isinstance(worker_raw, dict) else None)
            worker = _enrich_worker_dict(worker_prof, mw_map) if worker_prof else None

            enriched = _build_profile_response(p, student, faculty, worker)
            profiles.append(enriched)
        except Exception:
            pass

    return profiles


async def list_workers() -> list[ProfileResponse]:
    """List all worker profiles (for admin assignment dropdown)."""
    admin = get_supabase_admin()

    result = admin.table("profiles").select("*, worker_profiles(*)").eq("role", "worker").execute()

    mw_res = admin.table("master_workers").select("*").execute()
    mw_map = {str(mw["id"]): mw for mw in mw_res.data}

    profiles = []
    for p in result.data:
        try:
            worker_raw = p.get("worker_profiles")
            worker_prof = worker_raw[0] if isinstance(worker_raw, list) and worker_raw else (worker_raw if isinstance(worker_raw, dict) else None)
            worker = _enrich_worker_dict(worker_prof, mw_map) if worker_prof else None

            profiles.append(_build_profile_response(p, None, None, worker))
        except Exception:
            pass

    return profiles


async def update_profile(user: dict, data: UpdateProfileRequest) -> ProfileResponse:
    """Update the current user's profile (base + role-specific fields)."""
    admin = get_supabase_admin()
    profile_id = user["id"]

    # Update base profile fields
    base_updates = {}
    if data.name is not None:
        base_updates["name"] = data.name
    if data.phone is not None:
        base_updates["phone"] = data.phone

    if base_updates:
        admin.table("profiles").update(base_updates).eq("id", profile_id).execute()

    # Update role-specific fields
    if user["role"] == "student":
        student_updates = {}
        if data.roll_no is not None:
            student_updates["roll_no"] = data.roll_no
        if data.address is not None:
            student_updates["address"] = data.address
        if data.hostel is not None:
            student_updates["hostel"] = data.hostel

        if student_updates:
            admin.table("student_profiles").update(student_updates).eq("profile_id", profile_id).execute()

    elif user["role"] == "worker":
        worker_updates = {}
        if data.employee_id is not None:
            worker_updates["employee_id"] = data.employee_id
        if data.zone is not None:
            worker_updates["zone"] = data.zone

        if worker_updates:
            admin.table("worker_profiles").update(worker_updates).eq("profile_id", profile_id).execute()

    # Return updated profile
    return await get_profile_by_id(profile_id)
