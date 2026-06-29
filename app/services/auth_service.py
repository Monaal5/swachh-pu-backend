"""
Auth service — Implements multi-role registration flows (Student, Faculty, Worker)
and login rule verification based on system architecture diagram.
"""

import hashlib
import os
import secrets
from uuid import UUID
from fastapi import HTTPException, status

from app.models.auth import (
    StudentSignUpRequest,
    FacultySignUpRequest,
    WorkerSignUpRequest,
    LoginRequest,
    AuthResponse,
    AuthUser,
    WorkerMasterVerifyResponse,
)
from app.services.otp_service import generate_and_save_otp
from app.utils.supabase_client import get_supabase_admin


# ── Password Hashing Helpers ─────────────────────────────────

def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with HMAC-SHA256."""
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    ).hex()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify stored password hash."""
    try:
        salt, pwd_hash = stored_hash.split("$")
        recomputed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()
        return secrets.compare_digest(pwd_hash, recomputed)
    except Exception:
        return False


def generate_tokens(user_id: str, role: str) -> tuple[str, str]:
    """Generate mock JWT / session access & refresh tokens."""
    access_token = f"swachh_access_{user_id}_{secrets.token_hex(16)}"
    refresh_token = f"swachh_refresh_{user_id}_{secrets.token_hex(16)}"
    return access_token, refresh_token


# ── Master Worker Verification ───────────────────────────────

async def verify_worker_master(worker_id: str) -> WorkerMasterVerifyResponse:
    """Verify if Worker ID exists in MASTER_WORKERS table."""
    admin = get_supabase_admin()
    res = (
        admin.table("master_workers")
        .select("*")
        .eq("worker_id", worker_id.strip())
        .eq("status", "active")
        .execute()
    )
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid Worker ID or worker is inactive in master system.",
        )
    mw = res.data[0]
    return WorkerMasterVerifyResponse(
        master_worker_id=mw["id"],
        worker_id=mw["worker_id"],
        full_name=mw["full_name"],
        department=mw["department"],
        designation=mw["designation"],
        status=mw["status"],
    )


# ── Multi-Role Registration Flows ─────────────────────────────

async def signup_student(data: StudentSignUpRequest) -> AuthResponse:
    """1. Student Registration Flow."""
    admin = get_supabase_admin()

    # Check email uniqueness
    existing_user = admin.table("users").select("*").eq("email", data.email).execute()
    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    # Check roll_no uniqueness
    existing_roll = admin.table("student_profiles").select("*").eq("roll_no", data.roll_no).execute()
    if existing_roll.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Roll number is already registered.",
        )

    # Insert user
    pwd_hash = hash_password(data.password)
    user_res = (
        admin.table("users")
        .insert({
            "name": data.name,
            "email": data.email,
            "phone": data.phone,
            "password_hash": pwd_hash,
            "role": "student",
            "is_email_verified": False,
        })
        .execute()
    )
    user = user_res.data[0]

    # Insert student profile (students are automatically verified upon registration)
    admin.table("student_profiles").insert({
        "user_id": user["id"],
        "roll_no": data.roll_no,
        "verification_status": "verified",
    }).execute()


    # Generate OTP
    otp_code = await generate_and_save_otp(user["id"], data.email)

    return AuthResponse(
        user=AuthUser(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            phone=user.get("phone"),
            is_email_verified=False,
            verification_status="verified",
        ),
        message="Student registered successfully. Please verify your OTP sent to email.",
        otp_debug=otp_code,
    )



async def signup_faculty(data: FacultySignUpRequest) -> AuthResponse:
    """2. Faculty Registration Flow."""
    admin = get_supabase_admin()

    # Check email uniqueness
    existing_user = admin.table("users").select("*").eq("email", data.email).execute()
    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    # Check faculty_id uniqueness
    existing_fac = admin.table("faculty_profiles").select("*").eq("faculty_id", data.faculty_id).execute()
    if existing_fac.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faculty ID is already registered.",
        )

    # Insert user
    pwd_hash = hash_password(data.password)
    user_res = (
        admin.table("users")
        .insert({
            "name": data.name,
            "email": data.email,
            "phone": data.phone,
            "password_hash": pwd_hash,
            "role": "faculty",
            "is_email_verified": False,
        })
        .execute()
    )
    user = user_res.data[0]

    # Insert faculty profile
    admin.table("faculty_profiles").insert({
        "user_id": user["id"],
        "faculty_id": data.faculty_id,
        "faculty_type": data.faculty_type,
        "id_card_image": data.id_card_image,
        "verification_status": "pending",
    }).execute()

    # Generate OTP
    otp_code = await generate_and_save_otp(user["id"], data.email)

    return AuthResponse(
        user=AuthUser(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            phone=user.get("phone"),
            is_email_verified=False,
            verification_status="pending",
        ),
        message="Faculty registered successfully. Please verify your OTP sent to email and await ID verification.",
        otp_debug=otp_code,
    )


async def signup_worker(data: WorkerSignUpRequest) -> AuthResponse:
    """3. Worker Registration Flow."""
    admin = get_supabase_admin()

    # 1. Verify Master Worker ID
    mw_info = await verify_worker_master(data.worker_id)

    # Check email uniqueness
    existing_user = admin.table("users").select("*").eq("email", data.email).execute()
    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    # Insert user with full_name from master records
    pwd_hash = hash_password(data.password)
    user_res = (
        admin.table("users")
        .insert({
            "name": mw_info.full_name,
            "email": data.email,
            "phone": data.phone,
            "password_hash": pwd_hash,
            "role": "worker",
            "is_email_verified": False,
        })
        .execute()
    )
    user = user_res.data[0]

    # Insert worker profile with pending status
    admin.table("worker_profiles").insert({
        "user_id": user["id"],
        "master_worker_id": str(mw_info.master_worker_id),
        "id_card_image": data.id_card_image,
        "verification_status": "pending",
    }).execute()

    # Generate OTP
    otp_code = await generate_and_save_otp(user["id"], data.email)

    return AuthResponse(
        user=AuthUser(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            phone=user.get("phone"),
            is_email_verified=False,
            verification_status="pending",
        ),
        message="Your account is under verification. Please wait for admin approval.",
        otp_debug=otp_code,
    )


# ── Login & Rule Enforcement ─────────────────────────────────

async def login_user(data: LoginRequest) -> AuthResponse:
    """Login with email + password verification."""
    admin = get_supabase_admin()

    # Query user
    user_res = admin.table("users").select("*").eq("email", data.email).execute()
    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    user = user_res.data[0]

    # Verify password
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # ── Rule 1: Email must be verified ──
    if not user["is_email_verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email is not verified. Please verify your OTP first.",
        )

    # ── Rule 2: Fetch verification_status for role profile ──
    verification_status = "verified"
    role = user["role"]
    if role == "student":
        verification_status = "verified"

    elif role == "faculty":
        fp_res = admin.table("faculty_profiles").select("verification_status").eq("user_id", user["id"]).execute()
        if fp_res.data:
            verification_status = fp_res.data[0].get("verification_status", "pending")
    elif role == "worker":
        wp_res = admin.table("worker_profiles").select("verification_status").eq("user_id", user["id"]).execute()
        if wp_res.data:
            verification_status = wp_res.data[0].get("verification_status", "pending")

    access_token, refresh_token = generate_tokens(user["id"], user["role"])

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=AuthUser(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            phone=user.get("phone"),
            is_email_verified=user["is_email_verified"],
            verification_status=verification_status,
        ),
        message="Login successful",
    )
