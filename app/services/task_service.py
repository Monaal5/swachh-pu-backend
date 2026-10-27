"""
Task service — database queries for task CRUD and status transitions.
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.models.task import TaskCreateRequest, TaskResponse, TaskStatusResponse
from app.utils.db import get_db


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
        
        # Location Hierarchy fields
        location_id=row.get("location_id"),
        block_id=row.get("block_id"),
        floor_id=row.get("floor_id"),
        room_id=row.get("room_id"),
        location_name=row.get("location_name"),
        block_name=row.get("block_name"),
        floor_name=row.get("floor_name"),
        room_number=row.get("room_number"),
        room_name=row.get("room_name"),
    )


def _enrich_task_rows_batch(rows: list[dict], admin) -> list[dict]:
    """Perform batched lookups for profiles and locations/blocks/floors/rooms to avoid N+1 queries."""
    if not rows:
        return rows
        
    profile_ids = set()
    location_ids = set()
    block_ids = set()
    floor_ids = set()
    room_ids = set()
    
    for row in rows:
        if row.get("profile_id"):
            profile_ids.add(row["profile_id"])
        if row.get("assigned_to"):
            profile_ids.add(row["assigned_to"])
        if row.get("location_id"):
            location_ids.add(row["location_id"])
        if row.get("block_id"):
            block_ids.add(row["block_id"])
        if row.get("floor_id"):
            floor_ids.add(row["floor_id"])
        if row.get("room_id"):
            room_ids.add(row["room_id"])
            
    profiles_map = {}
    if profile_ids:
        res = admin.table("profiles").select("id, name").in_("id", list(profile_ids)).execute()
        profiles_map = {p["id"]: p["name"] for p in res.data}
        
    locations_map = {}
    if location_ids:
        res = admin.table("locations").select("id, name").in_("id", list(location_ids)).execute()
        locations_map = {l["id"]: l["name"] for l in res.data}
        
    blocks_map = {}
    if block_ids:
        res = admin.table("blocks").select("id, name").in_("id", list(block_ids)).execute()
        blocks_map = {b["id"]: b["name"] for b in res.data}
        
    floors_map = {}
    if floor_ids:
        res = admin.table("floors").select("id, name").in_("id", list(floor_ids)).execute()
        floors_map = {f["id"]: f["name"] for f in res.data}
        
    rooms_map = {}
    if room_ids:
        res = admin.table("rooms").select("id, room_number, name").in_("id", list(room_ids)).execute()
        rooms_map = {r["id"]: (r["room_number"], r["name"]) for r in res.data}
        
    for row in rows:
        row["creator_name"] = profiles_map.get(row.get("profile_id"))
        row["assignee_name"] = profiles_map.get(row.get("assigned_to")) if row.get("assigned_to") else None
        
        row["location_name"] = locations_map.get(row.get("location_id"))
        row["block_name"] = blocks_map.get(row.get("block_id"))
        row["floor_name"] = floors_map.get(row.get("floor_id"))
        
        room_info = rooms_map.get(row.get("room_id"))
        if room_info:
            row["room_number"] = room_info[0]
            row["room_name"] = room_info[1]
            
    return rows


async def create_task(data: TaskCreateRequest, profile_id: str) -> TaskResponse:
    """Create a new task (status defaults to 'pending' unless assigned_to is specified)."""
    admin = get_db()

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

    # Optional Location Hierarchy
    if data.location_id is not None:
        task_data["location_id"] = data.location_id
    if data.block_id is not None:
        task_data["block_id"] = data.block_id
    if data.floor_id is not None:
        task_data["floor_id"] = data.floor_id
    if data.room_id is not None:
        task_data["room_id"] = data.room_id

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

    enriched = _enrich_task_rows_batch(result.data, admin)[0]
    return _row_to_response(enriched)


async def get_task(task_id: str) -> TaskResponse:
    """Get a single task by ID."""
    admin = get_db()

    result = admin.table("tasks").select("*").eq("id", task_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task = result.data[0]
    enriched = _enrich_task_rows_batch([task], admin)[0]
    return _row_to_response(enriched)


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
    admin = get_db()

    query = admin.table("tasks").select("*", count="exact")

    if status_filter:
        query = query.eq("status", status_filter)
    if profile_id:
        query = query.eq("profile_id", profile_id)
    if assigned_to:
        query = query.eq("assigned_to", assigned_to)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

    result = query.execute()

    enriched_rows = _enrich_task_rows_batch(result.data, admin)
    tasks = [_row_to_response(row) for row in enriched_rows]
    total = result.count if result.count is not None else len(tasks)

    return tasks, total


async def get_my_tasks(profile_id: str) -> list[TaskResponse]:
    """Get tasks assigned to a specific worker."""
    admin = get_db()

    result = (
        admin.table("tasks")
        .select("*")
        .eq("assigned_to", profile_id)
        .order("created_at", desc=True)
        .execute()
    )

    enriched_rows = _enrich_task_rows_batch(result.data, admin)
    return [_row_to_response(row) for row in enriched_rows]


async def assign_task(task_id: str, worker_profile_id: str, due_date: Optional[datetime] = None) -> TaskStatusResponse:
    """Assign a pending task to a worker (admin action)."""
    admin = get_db()

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
    admin = get_db()

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
    admin = get_db()

    task = await get_task(task_id)
    if str(task.assigned_to) != worker_profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit verification for tasks assigned to you",
        )

    if task.status not in ("assigned", "rework_required"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit verification for task with status '{task.status}'. Status must be 'assigned' or 'rework_required'.",
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
    admin = get_db()

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
    admin = get_db()

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
    admin = get_db()

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

