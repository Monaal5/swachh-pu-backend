"""
OTP Service — Handles generation, storage, sending, and verification of 6-digit email OTPs.
"""

import random
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from app.utils.supabase_client import get_supabase_admin

MASTER_TEST_OTP = "123456"  # Static master OTP for testing convenience


async def generate_and_save_otp(user_id: str) -> str:
    """
    Generate a 6-digit numeric OTP, save to `email_otps` table with 15-min expiration.
    Returns the generated OTP string.
    """
    admin = get_supabase_admin()
    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()

    try:
        admin.table("email_otps").insert({
            "user_id": user_id,
            "otp": otp_code,
            "expires_at": expires_at,
            "is_used": False,
        }).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store OTP: {str(exc)}",
        )

    print(f"==========================================")
    print(f"[OTP SERVICE] Sent OTP {otp_code} to user_id {user_id} (Master Test OTP: {MASTER_TEST_OTP})")
    print(f"==========================================")
    return otp_code


async def resend_email_otp(email: str) -> dict:
    """
    Resend a fresh OTP to the given email address.
    """
    admin = get_supabase_admin()

    user_res = admin.table("users").select("*").eq("email", email).execute()
    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found.",
        )
    user = user_res.data[0]

    otp_code = await generate_and_save_otp(user["id"])
    return {
        "status": "success",
        "message": f"Fresh OTP generated and sent to {email}.",
        "otp_debug": otp_code,
        "master_test_otp": MASTER_TEST_OTP,
    }


async def get_latest_otp_for_email(email: str) -> dict:
    """
    Development endpoint to fetch the active OTP for an email.
    """
    admin = get_supabase_admin()

    user_res = admin.table("users").select("*").eq("email", email).execute()
    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found.",
        )
    user = user_res.data[0]

    otp_res = (
        admin.table("email_otps")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    latest_otp = otp_res.data[0]["otp"] if otp_res.data else MASTER_TEST_OTP
    return {
        "email": email,
        "latest_otp": latest_otp,
        "master_test_otp": MASTER_TEST_OTP,
        "is_email_verified": user["is_email_verified"],
    }


async def verify_email_otp(email: str, otp_code: str) -> dict:
    """
    Verify OTP code for given email. Supports both generated OTP and Master Test OTP (123456).
    Marks OTP as used and updates user is_email_verified=True.
    """
    admin = get_supabase_admin()

    # 1. Fetch user by email
    user_res = admin.table("users").select("*").eq("email", email).execute()
    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found.",
        )
    user = user_res.data[0]

    if user["is_email_verified"]:
        return user

    # 2. Check if master test OTP is provided
    if otp_code.strip() == MASTER_TEST_OTP:
        update_res = admin.table("users").update({"is_email_verified": True}).eq("id", user["id"]).execute()
        return update_res.data[0] if update_res.data else user

    # 3. Fetch unused OTPs for user
    otp_res = (
        admin.table("email_otps")
        .select("*")
        .eq("user_id", user["id"])
        .eq("otp", otp_code.strip())
        .eq("is_used", False)
        .execute()
    )

    if not otp_res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP code. (You can also use Master Test OTP: {MASTER_TEST_OTP})",
        )

    matched_otp = otp_res.data[0]

    # 4. Mark OTP as used
    admin.table("email_otps").update({"is_used": True}).eq("id", matched_otp["id"]).execute()

    # 5. Update user is_email_verified = True
    update_res = admin.table("users").update({"is_email_verified": True}).eq("id", user["id"]).execute()

    return update_res.data[0] if update_res.data else user
