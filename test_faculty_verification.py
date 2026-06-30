"""
Unit test for testing Faculty auto-verification and optional ID card image logic.
"""

from app.models.auth import FacultySignUpRequest, WorkerSignUpRequest
from app.dependencies import check_user_verification

def test_faculty_signup_request_validation():
    print("--- Testing FacultySignUpRequest Validation ---")
    
    # 1. Faculty SignUp Request without id_card_image
    payload = {
        "name": "Prof. Harpreet Singh",
        "email": "harpreet@pu.ac.in",
        "password": "securepassword123",
        "faculty_id": "FAC101",
        "faculty_type": "teaching",
        "phone": "9876543210"
    }
    
    req = FacultySignUpRequest(**payload)
    assert req.name == "Prof. Harpreet Singh"
    assert req.id_card_image is None
    print("FacultySignUpRequest validation (no ID card): OK")

def test_worker_signup_request_validation():
    print("--- Testing WorkerSignUpRequest Validation ---")
    
    # 2. Worker SignUp Request without id_card_image
    payload = {
        "email": "worker_new@example.com",
        "password": "securepassword123",
        "worker_id": "EMP104",
        "phone": "9876543211"
    }
    
    req = WorkerSignUpRequest(**payload)
    assert req.id_card_image is None
    print("WorkerSignUpRequest validation (no ID card): OK")

def test_user_verification_dependency():
    print("--- Testing check_user_verification dependency ---")
    
    # 3. Test that check_user_verification returns "verified" for faculty and worker
    faculty_user = {"id": "some-uuid", "role": "faculty"}
    worker_user = {"id": "some-uuid", "role": "worker"}
    student_user = {"id": "some-uuid", "role": "student"}
    admin_user = {"id": "some-uuid", "role": "admin"}
    
    import asyncio
    
    assert asyncio.run(check_user_verification(faculty_user)) == "verified"
    assert asyncio.run(check_user_verification(worker_user)) == "verified"
    assert asyncio.run(check_user_verification(student_user)) == "verified"
    assert asyncio.run(check_user_verification(admin_user)) == "verified"
    
    print("check_user_verification dependency returns 'verified' for all roles: OK")

if __name__ == "__main__":
    test_faculty_signup_request_validation()
    test_worker_signup_request_validation()
    test_user_verification_dependency()
    print("All faculty & worker auto-verification tests PASSED!\n")
