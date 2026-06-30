import re
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ── Common Validators ────────────────────────────────────────

def validate_email_str(v: str) -> str:
    if not isinstance(v, str):
        raise ValueError("Email must be a string.")
    v_stripped = v.strip()
    if not v_stripped:
        raise ValueError("Email cannot be empty.")
    if not EMAIL_REGEX.match(v_stripped):
        raise ValueError("Invalid email format.")
    return v_stripped


def validate_password_str(v: str) -> str:
    if not isinstance(v, str):
        raise ValueError("Password must be a string.")
    if not v or not v.strip():
        raise ValueError("Password cannot be empty.")
    if len(v) < 6:
        raise ValueError("Password must be at least 6 characters long.")
    return v


# ── Request Schemas ──────────────────────────────────────────

class StudentSignUpRequest(BaseModel):
    """Body for POST /auth/signup/student."""
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)
    roll_no: str = Field(..., min_length=1)
    phone: Optional[str] = None



    @field_validator("email", mode="before")
    @classmethod
    def val_email(cls, v: str) -> str:
        return validate_email_str(v)

    @field_validator("password", mode="before")
    @classmethod
    def val_password(cls, v: str) -> str:
        return validate_password_str(v)


class FacultySignUpRequest(BaseModel):
    """Body for POST /auth/signup/faculty."""
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)
    faculty_id: str = Field(..., min_length=1)
    faculty_type: Literal["teaching", "non_teaching"]
    id_card_image: str = Field(..., min_length=1, description="URL or path to uploaded ID card photo")
    phone: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def val_email(cls, v: str) -> str:
        clean_email = validate_email_str(v)
        if not clean_email.lower().endswith("pu.ac.in"):
            raise ValueError("Faculty email must belong to the official university domain (pu.ac.in).")
        return clean_email

    @field_validator("password", mode="before")
    @classmethod
    def val_password(cls, v: str) -> str:
        return validate_password_str(v)


class WorkerSignUpRequest(BaseModel):
    """Body for POST /auth/signup/worker."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    worker_id: str = Field(..., min_length=1, description="Master Worker ID e.g. EMP101")
    id_card_image: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def val_email(cls, v: str) -> str:
        return validate_email_str(v)

    @field_validator("password", mode="before")
    @classmethod
    def val_password(cls, v: str) -> str:
        return validate_password_str(v)


class VerifyOTPRequest(BaseModel):
    """Body for POST /auth/verify-otp."""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class ResendOTPRequest(BaseModel):
    """Body for POST /auth/resend-otp."""
    email: EmailStr


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""
    email: EmailStr
    password: str


class AdminUserDecisionRequest(BaseModel):
    """Body for POST /admin/users/{profile_id}/verify."""
    action: Literal["approve", "reject"]
    rejection_reason: Optional[str] = None


# Backward compatibility alias
AdminWorkerDecisionRequest = AdminUserDecisionRequest


# ── Response Schemas ─────────────────────────────────────────

class WorkerMasterVerifyResponse(BaseModel):
    """Returned when checking master worker table."""
    master_worker_id: UUID
    worker_id: str
    full_name: str
    department: str
    designation: str
    status: str


class AuthUser(BaseModel):
    """User info returned after auth."""
    id: UUID
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    is_email_verified: bool
    verification_status: Optional[str] = None


class AuthResponse(BaseModel):
    """Returned on successful login / signup / otp verification."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[AuthUser] = None
    message: str = "success"
    otp_debug: Optional[str] = None  # Returned for testing/dev environment convenience


class PendingUserResponse(BaseModel):
    """User profile application pending admin review."""
    profile_id: UUID
    user_id: UUID
    name: str
    email: str
    role: str
    phone: Optional[str] = None
    id_card_image: Optional[str] = None
    verification_status: str
    created_at: datetime
    details: Optional[dict] = None


# Backward compatibility alias
PendingWorkerResponse = PendingUserResponse

