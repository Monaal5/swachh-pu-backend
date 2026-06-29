"""
Pydantic schemas for task endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────────

class TaskCreateRequest(BaseModel):
    """Body for POST /tasks/  — create a new task/complaint."""

    photo_url: str = Field(..., description="Public URL of the uploaded photo")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    description: str = Field(..., min_length=1, description="Text description of the issue")
    audio_url: Optional[str] = Field(None, description="Public URL of optional audio recording")
    due_date: Optional[datetime] = Field(None, description="Optional target completion due date")
    assigned_to: Optional[UUID] = Field(None, description="Optional profile ID of worker to assign immediately upon task creation")



class TaskAssignRequest(BaseModel):
    """Body for PATCH /tasks/{task_id}/assign."""

    worker_profile_id: UUID = Field(..., description="Profile ID of the worker to assign")
    due_date: Optional[datetime] = Field(None, description="Optional target completion due date")


class TaskSubmitVerificationRequest(BaseModel):
    """Body for PATCH /tasks/{task_id}/submit-verification."""

    completion_photo_url: str = Field(..., description="Public URL of the cleaned area photo proof")


class TaskRejectVerificationRequest(BaseModel):
    """Body for PATCH /tasks/{task_id}/reject-verification."""

    rejection_reason: str = Field(..., min_length=1, description="Reason for rejecting completion proof")


# ── Response Schemas ─────────────────────────────────────────

class TaskResponse(BaseModel):
    """Single task detail."""

    id: UUID
    photo_url: str
    latitude: float
    longitude: float
    audio_url: Optional[str] = None
    description: str
    profile_id: UUID
    assigned_to: Optional[UUID] = None
    status: str
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
    completion_photo_url: Optional[str] = None
    completion_submitted_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Optional: creator & assignee names (populated via join)
    creator_name: Optional[str] = None
    assignee_name: Optional[str] = None


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""

    tasks: list[TaskResponse]
    count: int


class TaskStatusResponse(BaseModel):
    """Returned after a status change (assign / reject / complete)."""

    task_id: UUID
    new_status: str
    message: str = "status updated"

