"""
Auth router — Handles multi-role registration flows, OTP verification, master worker validation, and login.
"""

from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.models.auth import (
    StudentSignUpRequest,
    FacultySignUpRequest,
    WorkerSignUpRequest,
    VerifyOTPRequest,
    ResendOTPRequest,
    LoginRequest,
    AuthResponse,
    WorkerMasterVerifyResponse,
)
from app.services import auth_service, otp_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup/student", response_model=AuthResponse, status_code=201)
async def signup_student(data: StudentSignUpRequest):
    """Register a new student account."""
    return await auth_service.signup_student(data)


@router.post("/signup/faculty", response_model=AuthResponse, status_code=201)
async def signup_faculty(data: FacultySignUpRequest):
    """Register a new faculty account."""
    return await auth_service.signup_faculty(data)


@router.get("/worker/verify-master/{worker_id}", response_model=WorkerMasterVerifyResponse)
async def verify_worker_master(worker_id: str):
    """Verify if Worker ID exists in MASTER_WORKERS table."""
    return await auth_service.verify_worker_master(worker_id)


@router.post("/signup/worker", response_model=AuthResponse, status_code=201)
async def signup_worker(data: WorkerSignUpRequest):
    """Register a new worker account (subject to admin approval)."""
    return await auth_service.signup_worker(data)


@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest):
    """Verify email OTP code. Accepts generated 6-digit OTP or Master Test OTP (123456)."""
    updated_user = await otp_service.verify_email_otp(data.email, data.otp)
    return {"status": "success", "message": "Email verified successfully.", "user_id": updated_user["id"]}


@router.post("/resend-otp")
async def resend_otp(data: ResendOTPRequest):
    """Resend a fresh OTP to user's email."""
    return await otp_service.resend_email_otp(data.email)


@router.get("/latest-otp/{email}")
async def get_latest_otp(email: str):
    """Development helper endpoint to inspect the latest active OTP for an email."""
    return await otp_service.get_latest_otp_for_email(email)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """Login with email + password."""
    return await auth_service.login_user(data)


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Logout current user."""
    return {"message": "Logged out successfully."}
