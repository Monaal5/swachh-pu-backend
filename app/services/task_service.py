"""
Task service — Supabase queries for task CRUD and status transitions.
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.models.task import TaskCreateRequest, TaskResponse, TaskStatusResponse
from app.utils.supabase_client import get_supabase_admin


from datetime import datetime, timezone

def _row_to_response(row: dict) -> TaskResponse:
    """Convert a raw DB row to TaskResponse."""
    return TaskResponse(
        id=row["id"],
        photo_url=row["photo_url"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        audio_url=row.get("audio_url"),
        description=row["description"],
        profile_id=row["profile_id"],
        assigned_to=row.get("assigned_to"),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        due_date=row.get("due_date"),
        completion_photo_url=row.get("completion_photo_url"),
        completion_submitted_at=row.get("completion_submitted_at"),
        rejection_reason=row.get("rejection_reason"),
        creator_name=row.get("creator_name"),
        assignee_name=row.get("assignee_name"),
    )


async def create_task(data: TaskCreateRequest, profile_id: str) -> TaskResponse:
    """Create a new task (status defaults to 'pending' unless assigned_to is specified)."""
    admin = get_supabase_admin()

    initial_status = "assigned" if data.assigned_to else "pending"
    task_data = {
        "photo_url": data.photo_url,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "audio_url": data.audio_url,
        "description": data.description,
        "profile_id": profile_id,
        "status": initial_status,
    }
    if data.due_date:
        task_data["due_date"] = data.due_date.isoformat()
    if data.assigned_to:
        task_data["assigned_to"] = str(data.assigned_to)


    try:
        result = admin.table("tasks").insert(task_data).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(exc)}",
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task creation returned no data",
        )

    return _row_to_response(result.data[0])


async def get_task(task_id: str) -> TaskResponse:
    """Get a single task by ID."""
    admin = get_supabase_admin()

    result = admin.table("tasks").select("*").eq("id", task_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task = result.data[0]

    # Enrich with creator name
    creator_result = admin.table("profiles").select("name").eq("id", task["profile_id"]).execute()
    if creator_result.data:
        task["creator_name"] = creator_result.data[0]["name"]

    # Enrich with assignee name
    if task.get("assigned_to"):
        assignee_result = admin.table("profiles").select("name").eq("id", task["assigned_to"]).execute()
        if assignee_result.data:
            task["assignee_name"] = assignee_result.data[0]["name"]

    return _row_to_response(task)


async def list_tasks(
    status_filter: Optional[str] = None,
    profile_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TaskResponse], int]:
    """
    List tasks with optional filters.
    Returns (tasks, total_count).
    """
    admin = get_supabase_admin()

    query = admin.table("tasks").select("*", count="exact")

    if status_filter:
        query = query.eq("status", status_filter)
    if profile_id:
        query = query.eq("profile_id", profile_id)
    if assigned_to:
        query = query.eq("assigned_to", assigned_to)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

    result = query.execute()

    tasks = [_row_to_response(row) for row in result.data]
    total = result.count if result.count is not None else len(tasks)

    return tasks, total


async def get_my_tasks(profile_id: str) -> list[TaskResponse]:
    """Get tasks assigned to a specific worker."""
    admin = get_supabase_admin()

    result = (
        admin.table("tasks")
        .select("*")
        .eq("assigned_to", profile_id)
        .order("created_at", desc=True)
        .execute()
    )

    return [_row_to_response(row) for row in result.data]


async def assign_task(task_id: str, worker_profile_id: str, due_date: Optional[datetime] = None) -> TaskStatusResponse:
    """Assign a pending task to a worker (admin action)."""
    admin = get_supabase_admin()

    # Verify task exists and is in valid state
    task = await get_task(task_id)
    if task.status not in ("pending", "rework_required", "assigned"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign a task with status '{task.status}'.",
        )

    # Verify worker exists and is actually a worker
    worker_result = admin.table("profiles").select("*").eq("id", worker_profile_id).execute()
    if not worker_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    if worker_result.data[0]["role"] != "worker":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected profile is not a worker")

    update_payload = {
        "assigned_to": worker_profile_id,
        "status": "assigned",
    }
    if due_date:
        update_payload["due_date"] = due_date.isoformat()

    # Update task
    admin.table("tasks").update(update_payload).eq("id", task_id).execute()

    return TaskStatusResponse(task_id=task_id, new_status="assigned", message="Task assigned to worker")


async def reject_task(task_id: str) -> TaskStatusResponse:
    """Reject a pending task (admin action)."""
    admin = get_supabase_admin()

    task = await get_task(task_id)
    if task.status not in ("pending",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject a task with status '{task.status}'. Only 'pending' tasks can be rejected.",
        )

    admin.table("tasks").update({"status": "rejected"}).eq("id", task_id).execute()

    return TaskStatusResponse(task_id=task_id, new_status="rejected", message="Task rejected")


async def submit_task_verification(
    task_id: str,
    worker_profile_id: str,
    completion_photo_url: str,
) -> TaskStatusResponse:
    """Submit proof photo for task verification (worker action)."""
    admin = get_supabase_admin()

    task = await get_task(task_id)
    if task.status not in ("assigned", "rework_required"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit verification for task with status '{task.status}'. Status must be 'assigned' or 'rework_required'.",
        )

    if str(task.assigned_to) != worker_profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit verification for tasks assigned to you",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    admin.table("tasks").update({
        "status": "pending_verification",
        "completion_photo_url": completion_photo_url,
        "completion_submitted_at": now_iso,
    }).eq("id", task_id).execute()

    return TaskStatusResponse(
        task_id=task_id,
        new_status="pending_verification",
        message="Task completion photo submitted for admin verification",
    )


async def approve_task_verification(task_id: str) -> TaskStatusResponse:
    """Approve completed task photo proof (admin action)."""
    admin = get_supabase_admin()

    task = await get_task(task_id)
    if task.status != "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve task with status '{task.status}'. Only 'pending_verification' tasks can be approved.",
        )

    admin.table("tasks").update({"status": "completed"}).eq("id", task_id).execute()

    return TaskStatusResponse(
        task_id=task_id,
        new_status="completed",
        message="Task completion approved and marked as completed",
    )


async def reject_task_verification(task_id: str, rejection_reason: str) -> TaskStatusResponse:
    """Reject completed task photo proof and request rework (admin action)."""
    admin = get_supabase_admin()

    task = await get_task(task_id)
    if task.status != "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject verification for task with status '{task.status}'. Only 'pending_verification' tasks can be rejected.",
        )

    admin.table("tasks").update({
        "status": "rework_required",
        "rejection_reason": rejection_reason,
    }).eq("id", task_id).execute()

    return TaskStatusResponse(
        task_id=task_id,
        new_status="rework_required",
        message=f"Task verification rejected and sent back to worker for rework: {rejection_reason}",
    )


async def complete_task(task_id: str, worker_profile_id: str) -> TaskStatusResponse:
    """Legacy complete endpoint alias for backward compatibility."""
    admin = get_supabase_admin()

    task = await get_task(task_id)
    if task.status not in ("assigned", "pending_verification"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete a task with status '{task.status}'.",
        )

    if str(task.assigned_to) != worker_profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only complete tasks assigned to you",
        )

    admin.table("tasks").update({"status": "completed"}).eq("id", task_id).execute()

    return TaskStatusResponse(task_id=task_id, new_status="completed", message="Task completed")

