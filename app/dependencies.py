"""
FastAPI dependencies — injectable auth & role checks.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.supabase_client import get_supabase_client, get_supabase_admin

security = HTTPBearer(auto_error=True)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Extract and verify token from Authorization header.
    Returns the user row from the `users` table.
    """
    token = credentials.credentials
    admin_client = get_supabase_admin()

    # If mock/custom token format e.g. swachh_access_{user_id}_...
    if token.startswith("swachh_access_"):
        try:
            parts = token.split("_")
            user_id = parts[2]
            res = admin_client.table("users").select("*").eq("id", user_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    # Standard Supabase JWT fallback
    supabase = get_supabase_client()
    try:
        user_response = supabase.auth.get_user(token)
        auth_user = user_response.user
        if auth_user is not None:
            res = admin_client.table("users").select("*").eq("id", str(auth_user.id)).execute()
            if res.data:
                return res.data[0]
            # fallback check profiles if users record missing
            prof_res = admin_client.table("profiles").select("*").eq("user_id", str(auth_user.id)).execute()
            if prof_res.data:
                return prof_res.data[0]
    except Exception:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
    )


async def check_user_verification(user: dict) -> str:
    """Helper to check verification_status for user's role profile."""
    role = user.get("role")
    if role in ("admin", "student"):
        return "verified"

    admin_client = get_supabase_admin()
    if role == "faculty":
        fp_res = admin_client.table("faculty_profiles").select("verification_status").eq("user_id", user["id"]).execute()
        if fp_res.data:
            return fp_res.data[0].get("verification_status", "pending")

    elif role == "worker":
        wp_res = admin_client.table("worker_profiles").select("verification_status").eq("user_id", user["id"]).execute()
        if wp_res.data:
            return wp_res.data[0].get("verification_status", "pending")
    return "verified"


async def require_verified_user(user: dict = Depends(get_current_user)):
    """
    Dependency ensuring current user is verified by admin.
    """
    status_str = await check_user_verification(user)
    if status_str != "verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your identity card verification is pending or rejected by admin.",
        )
    return user


def require_role(*allowed_roles: str):
    """
    Dependency checking if current user has one of allowed roles and is verified.
    """
    async def _check_role(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {', '.join(allowed_roles)}",
            )
        status_str = await check_user_verification(user)
        if status_str != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your identity card verification is pending or rejected by admin.",
            )
        return user

    return _check_role

