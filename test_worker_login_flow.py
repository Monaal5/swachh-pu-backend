import asyncio
from unittest.mock import MagicMock, patch
from app.models.auth import LoginRequest
from app.services import auth_service, profile_service
from app.models.profile import ProfileResponse

# Define mock data for master workers
MOCK_MASTER_WORKER = {
    "id": "11111111-1111-1111-1111-111111111111",
    "worker_id": "EMP101",
    "full_name": "Ramesh Kumar",
    "department": "Sanitation",
    "phone": "9876543210",
    "designation": "Senior Sanitation Officer",
    "status": "active",
    "username": "ramesh101",
    "password": "pass101",
    "address": "123, Green Street, City, State",
    "date_of_joining": "2022-06-01"
}

MOCK_USER_RECORD = {
    "id": "22222222-2222-2222-2222-222222222222",
    "name": "Ramesh Kumar",
    "email": "ramesh101@worker.swachh.pu",
    "phone": "9876543210",
    "password_hash": "mockedhash",
    "role": "worker",
    "is_email_verified": True,
    "created_at": "2026-07-03T12:00:00+00:00"
}

MOCK_WORKER_PROFILE = {
    "id": "33333333-3333-3333-3333-333333333333",
    "user_id": MOCK_USER_RECORD["id"],
    "master_worker_id": MOCK_MASTER_WORKER["id"],
    "zone": "Sector 14",
    "id_card_image": None,
    "verification_status": "verified"
}

MOCK_PROFILE_RECORD = {
    "id": MOCK_USER_RECORD["id"],
    "user_id": MOCK_USER_RECORD["id"],
    "name": "Ramesh Kumar",
    "role": "worker",
    "phone": "9876543210",
    "created_at": "2026-07-03T12:00:00+00:00"
}

# Chainable Mock helper to support any number of chained methods like .select().eq().eq().execute()
class ChainableMock:
    def __init__(self, data_to_return):
        self.data_to_return = data_to_return
        
    def select(self, *args, **kwargs):
        return self
        
    def eq(self, *args, **kwargs):
        return self
        
    def insert(self, *args, **kwargs):
        return self
        
    def execute(self):
        m = MagicMock()
        m.data = self.data_to_return
        return m

async def test_flow():
    print("=== Testing Worker Login & Profile Flow ===")
    
    mock_supabase = MagicMock()

    # Mock the table queries using ChainableMock
    def table_mock(table_name):
        if table_name == "master_workers":
            return ChainableMock([MOCK_MASTER_WORKER])
        elif table_name == "worker_profiles":
            return ChainableMock([MOCK_WORKER_PROFILE])
        elif table_name == "users":
            return ChainableMock([MOCK_USER_RECORD])
        elif table_name == "profiles":
            return ChainableMock([MOCK_PROFILE_RECORD])
        return ChainableMock([])

    mock_supabase.table = MagicMock(side_effect=table_mock)
    
    # Patch the get_supabase_admin to return our mock
    with patch("app.services.auth_service.get_supabase_admin", return_value=mock_supabase), \
         patch("app.services.profile_service.get_supabase_admin", return_value=mock_supabase):
        
        # 1. Login
        login_req = LoginRequest(email="ramesh101", password="pass101")
        print("\n[Step 1] Attempting worker login...")
        login_res = await auth_service.login_user(login_req)
        
        print("Login Success!")
        print(f"  Access Token: {login_res.access_token}")
        print(f"  Role: {login_res.user.role}")
        print(f"  Verification Status: {login_res.user.verification_status}")
        
        assert login_res.user.role == "worker"
        assert login_res.user.verification_status == "verified"
        assert "swachh_access_" in login_res.access_token
        
        # 2. Get Profile Detail
        print("\n[Step 2] Fetching enriched worker profile...")
        profile_res = await profile_service.get_profile_by_id(MOCK_USER_RECORD["id"])
        
        print("Profile Fetch Success!")
        print(f"  Name: {profile_res.name}")
        print(f"  Role: {profile_res.role}")
        
        detail = profile_res.worker_detail
        print(f"  Employee ID: {detail.employee_id}")
        print(f"  Address: {detail.address}")
        print(f"  Department: {detail.department}")
        print(f"  Date of Joining: {detail.date_of_joining}")
        print(f"  Status: {detail.status}")
        print(f"  Designation: {detail.designation}")
        
        assert detail.employee_id == "EMP101"
        assert detail.address == "123, Green Street, City, State"
        assert detail.department == "Sanitation"
        assert detail.date_of_joining == "2022-06-01"
        assert detail.status == "active"
        assert detail.designation == "Senior Sanitation Officer"
        
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_flow())
