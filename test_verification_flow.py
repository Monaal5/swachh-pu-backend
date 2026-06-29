"""
Verification script for Worker Task Completion and Verification Flow models and routes.
"""

from datetime import datetime
from uuid import uuid4
from app.models.task import (
    TaskCreateRequest,
    TaskAssignRequest,
    TaskSubmitVerificationRequest,
    TaskRejectVerificationRequest,
    TaskResponse,
)

def test_models():
    print("--- Testing Verification Models ---")
    
    # 1. Test TaskCreateRequest with due_date & assigned_to
    worker_id = uuid4()
    create_req = TaskCreateRequest(
        photo_url="http://example.com/photo.jpg",
        latitude=30.75,
        longitude=76.78,
        description="Clean library main hall",
        due_date=datetime.now(),
        assigned_to=worker_id
    )
    assert create_req.description == "Clean library main hall"
    assert create_req.assigned_to == worker_id
    print("TaskCreateRequest with due_date & assigned_to: OK")


    # 2. Test TaskSubmitVerificationRequest
    submit_req = TaskSubmitVerificationRequest(
        completion_photo_url="http://example.com/clean_proof.jpg"
    )
    assert submit_req.completion_photo_url == "http://example.com/clean_proof.jpg"
    print("TaskSubmitVerificationRequest: OK")

    # 3. Test TaskRejectVerificationRequest
    reject_req = TaskRejectVerificationRequest(
        rejection_reason="The trash cans behind building 3 were not emptied."
    )
    assert reject_req.rejection_reason == "The trash cans behind building 3 were not emptied."
    print("TaskRejectVerificationRequest: OK")

    # 4. Test TaskResponse serialization
    task_res = TaskResponse(
        id=uuid4(),
        photo_url="http://example.com/photo.jpg",
        latitude=30.75,
        longitude=76.78,
        description="Clean library main hall",
        profile_id=uuid4(),
        status="pending_verification",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=datetime.now(),
        completion_photo_url="http://example.com/clean_proof.jpg",
        completion_submitted_at=datetime.now(),
        rejection_reason=None
    )
    assert task_res.status == "pending_verification"
    print("TaskResponse with completion fields: OK")
    print("All verification model tests PASSED!\n")


def test_fastapi_app_import():
    print("--- Testing FastAPI App Router Registration ---")
    from app.main import app
    routes = [route.path for route in app.routes]
    
    expected_routes = [
        "/tasks/{task_id}/submit-verification",
        "/tasks/{task_id}/approve",
        "/tasks/{task_id}/reject-verification",
    ]
    
    for route in expected_routes:
        assert route in routes, f"Missing route {route} in FastAPI app"
        print(f"Found registered route: {route}")
        
    print("FastAPI router integration PASSED!\n")


if __name__ == "__main__":
    test_models()
    test_fastapi_app_import()
    print("SUCCESS: All verification flow checks passed!")
