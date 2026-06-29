"""
End-to-End Integration Test for Worker Task Completion and Verification Flow.
Tests API route logic, role authentication, state machine transitions, and error handling.
"""

import sys
from datetime import datetime
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user, require_role, require_verified_user
from app.services import task_service
from app.models.task import TaskResponse, TaskStatusResponse

# Global test variables to simulate mock database state
MOCK_TASK_ID = str(uuid4())
MOCK_WORKER_ID = str(uuid4())
MOCK_CREATOR_ID = str(uuid4())

# In-memory task store for robust E2E test state simulation
mock_db_tasks = {}

def reset_mock_db():
    global mock_db_tasks
    mock_db_tasks = {
        MOCK_TASK_ID: {
            "id": MOCK_TASK_ID,
            "photo_url": "https://storage.example.com/initial.jpg",
            "latitude": 30.75,
            "longitude": 76.78,
            "audio_url": None,
            "description": "Clean student centre plaza",
            "profile_id": MOCK_CREATOR_ID,
            "assigned_to": MOCK_WORKER_ID,
            "status": "assigned",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "due_date": datetime.now().isoformat(),
            "completion_photo_url": None,
            "completion_submitted_at": None,
            "rejection_reason": None,
            "creator_name": "Student Alex",
            "assignee_name": "Worker Ramesh"
        }
    }

# Mock service implementations replacing live database calls for deterministic E2E verification
async def mock_get_task(task_id: str):
    if task_id not in mock_db_tasks:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    data = mock_db_tasks[task_id]
    return TaskResponse(**data)

async def mock_submit_task_verification(task_id: str, worker_profile_id: str, completion_photo_url: str):
    task = await mock_get_task(task_id)
    if str(task.assigned_to) != worker_profile_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="You can only submit verification for tasks assigned to you")
    if task.status not in ("assigned", "rework_required"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Cannot submit verification for task with status '{task.status}'.")

    
    mock_db_tasks[task_id]["status"] = "pending_verification"
    mock_db_tasks[task_id]["completion_photo_url"] = completion_photo_url
    mock_db_tasks[task_id]["completion_submitted_at"] = datetime.now().isoformat()
    return TaskStatusResponse(task_id=task_id, new_status="pending_verification", message="Submitted for verification")

async def mock_approve_task_verification(task_id: str):
    task = await mock_get_task(task_id)
    if task.status != "pending_verification":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Cannot approve task with status '{task.status}'.")
    mock_db_tasks[task_id]["status"] = "completed"
    return TaskStatusResponse(task_id=task_id, new_status="completed", message="Approved and completed")

async def mock_reject_task_verification(task_id: str, rejection_reason: str):
    task = await mock_get_task(task_id)
    if task.status != "pending_verification":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Cannot reject verification for task with status '{task.status}'.")
    mock_db_tasks[task_id]["status"] = "rework_required"
    mock_db_tasks[task_id]["rejection_reason"] = rejection_reason
    return TaskStatusResponse(task_id=task_id, new_status="rework_required", message=f"Rejected: {rejection_reason}")

def run_e2e_suite():
    print("=========================================================")
    print(" Running Full E2E Worker Task Verification Suite ")
    print("=========================================================\n")
    
    # Monkeypatch task_service methods for API testing
    task_service.get_task = mock_get_task
    task_service.submit_task_verification = mock_submit_task_verification
    task_service.approve_task_verification = mock_approve_task_verification
    task_service.reject_task_verification = mock_reject_task_verification
    
    client = TestClient(app)
    
    # -----------------------------------------------------------------
    # SCENARIO 1: Worker Submits Task Evidence (Assigned -> Pending Verification)
    # -----------------------------------------------------------------
    reset_mock_db()
    print("[Test 1] Worker submits task completion photo proof...")
    
    # Mock authentication as worker
    app.dependency_overrides[get_current_user] = lambda: {"id": MOCK_WORKER_ID, "role": "worker"}
    app.dependency_overrides[require_role("worker")] = lambda: {"id": MOCK_WORKER_ID, "role": "worker"}
    
    res = client.patch(
        f"/tasks/{MOCK_TASK_ID}/submit-verification",
        json={"completion_photo_url": "https://storage.example.com/clean_proof_1.jpg"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["new_status"] == "pending_verification"
    assert mock_db_tasks[MOCK_TASK_ID]["status"] == "pending_verification"
    assert mock_db_tasks[MOCK_TASK_ID]["completion_photo_url"] == "https://storage.example.com/clean_proof_1.jpg"
    print(" -> PASSED: Task status updated to 'pending_verification' with photo proof!\n")
    
    # -----------------------------------------------------------------
    # SCENARIO 2: Admin Approves Completion Proof (Pending Verification -> Completed)
    # -----------------------------------------------------------------
    print("[Test 2] Admin reviews and approves completion proof...")
    app.dependency_overrides[get_current_user] = lambda: {"id": str(uuid4()), "role": "admin"}
    app.dependency_overrides[require_role("admin")] = lambda: {"id": str(uuid4()), "role": "admin"}
    
    res = client.patch(f"/tasks/{MOCK_TASK_ID}/approve")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["new_status"] == "completed"
    assert mock_db_tasks[MOCK_TASK_ID]["status"] == "completed"
    print(" -> PASSED: Task status successfully transitioned to 'completed'!\n")
    
    # -----------------------------------------------------------------
    # SCENARIO 3: Rejection & Rework Lifecycle (Pending Verification -> Rework Required -> Pending Verification)
    # -----------------------------------------------------------------
    reset_mock_db()
    mock_db_tasks[MOCK_TASK_ID]["status"] = "pending_verification"
    mock_db_tasks[MOCK_TASK_ID]["completion_photo_url"] = "https://storage.example.com/bad_proof.jpg"
    
    print("[Test 3] Admin rejects proof and requests rework...")
    res = client.patch(
        f"/tasks/{MOCK_TASK_ID}/reject-verification",
        json={"rejection_reason": "Corner bins were not cleaned properly."}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["new_status"] == "rework_required"
    assert mock_db_tasks[MOCK_TASK_ID]["status"] == "rework_required"
    assert mock_db_tasks[MOCK_TASK_ID]["rejection_reason"] == "Corner bins were not cleaned properly."
    print(" -> PASSED: Task status set to 'rework_required' with feedback reason!\n")
    
    print("[Test 4] Worker re-submits new photo proof after rework...")
    app.dependency_overrides[get_current_user] = lambda: {"id": MOCK_WORKER_ID, "role": "worker"}
    app.dependency_overrides[require_role("worker")] = lambda: {"id": MOCK_WORKER_ID, "role": "worker"}
    
    res = client.patch(
        f"/tasks/{MOCK_TASK_ID}/submit-verification",
        json={"completion_photo_url": "https://storage.example.com/fixed_proof.jpg"}
    )
    assert res.status_code == 200
    assert mock_db_tasks[MOCK_TASK_ID]["status"] == "pending_verification"
    assert mock_db_tasks[MOCK_TASK_ID]["completion_photo_url"] == "https://storage.example.com/fixed_proof.jpg"
    print(" -> PASSED: Worker successfully resubmitted proof photo after rework!\n")
    
    # -----------------------------------------------------------------
    # SCENARIO 4: Security & Permission Guard Checks
    # -----------------------------------------------------------------
    reset_mock_db()
    print("[Test 5] Security Check: Unauthorized worker attempts submission on another worker's task...")

    other_worker_id = str(uuid4())
    app.dependency_overrides[get_current_user] = lambda: {"id": other_worker_id, "role": "worker"}
    app.dependency_overrides[require_role("worker")] = lambda: {"id": other_worker_id, "role": "worker"}
    
    res = client.patch(
        f"/tasks/{MOCK_TASK_ID}/submit-verification",
        json={"completion_photo_url": "https://storage.example.com/hacked.jpg"}
    )
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print(" -> PASSED: Forbidden 403 correctly returned for unauthorized worker!\n")

    # Clean up overrides
    app.dependency_overrides.clear()
    
    print("=========================================================")
    print(" ALL E2E VERIFICATION SUITE TESTS PASSED SUCCESSFULLY! ")
    print("=========================================================")

if __name__ == "__main__":
    run_e2e_suite()
