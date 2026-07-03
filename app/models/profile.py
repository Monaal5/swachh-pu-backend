"""
Pydantic schemas for profile endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Sub-schemas ──────────────────────────────────────────────

class StudentProfileDetail(BaseModel):
    """Student-specific fields."""

    roll_no: str
    id_card_image: Optional[str] = None
    verification_status: Optional[str] = "pending"
    address: Optional[str] = None
    hostel: Optional[str] = None


class FacultyProfileDetail(BaseModel):
    """Faculty-specific fields."""

    faculty_id: str
    faculty_type: str
    id_card_image: Optional[str] = None
    verification_status: Optional[str] = "pending"


class WorkerProfileDetail(BaseModel):
    """Worker-specific fields."""

    employee_id: Optional[str] = None
    zone: Optional[str] = None
    id_card_image: Optional[str] = None
    verification_status: Optional[str] = "pending"
    address: Optional[str] = None
    date_of_joining: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    designation: Optional[str] = None


# ── Response Schemas ─────────────────────────────────────────

class ProfileResponse(BaseModel):
    """Full profile response (base + role-specific details)."""

    id: UUID
    user_id: UUID
    name: str
    role: str
    phone: Optional[str] = None
    created_at: datetime

    # Populated based on role
    student_detail: Optional[StudentProfileDetail] = None
    faculty_detail: Optional[FacultyProfileDetail] = None
    worker_detail: Optional[WorkerProfileDetail] = None


class ProfileListResponse(BaseModel):
    """Paginated list of profiles."""

    profiles: list[ProfileResponse]
    count: int


# ── Request Schemas ──────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    """Body for PUT /profiles/me — all fields optional."""

    name: Optional[str] = Field(None, min_length=1)
    phone: Optional[str] = None

    # Student fields
    roll_no: Optional[str] = None
    address: Optional[str] = None
    hostel: Optional[str] = None

    # Worker fields
    employee_id: Optional[str] = None
    zone: Optional[str] = None
