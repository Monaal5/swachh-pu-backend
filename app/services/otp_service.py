"""
OTP Service — Handles generation, storage, sending, and verification of 6-digit email OTPs.
"""

import asyncio
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from app.utils.supabase_client import get_supabase_admin
from app.config import get_settings

MASTER_TEST_OTP = "123456"  # Static master OTP for testing convenience


import traceback
from email.utils import formataddr
import httpx


def send_otp_email(recipient_email: str, otp_code: str):
    """Send OTP code via HTTP API (Resend/Brevo) or SMTP if configured."""
    settings = get_settings()
    subject = "Swachh PU - Your Verification OTP Code"
    body = (
        f"Hello,\n\nYour Swachh PU email verification OTP code is: {otp_code}\n\n"
        f"This code will expire in 15 minutes.\n\n"
        f"If you did not request this code, please ignore this email."
    )
    from_header = settings.emails_from or "Swachh PU <onboarding@resend.dev>"

    # 1. Try Resend HTTP API (Ideal for Render / cloud environments where SMTP ports are blocked)
    resend_key = settings.resend_api_key.strip() if settings.resend_api_key else ""
    if resend_key:
        try:
            print("[OTP SERVICE] Sending email via Resend HTTP API...")
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "from": settings.emails_from or "Swachh PU <onboarding@resend.dev>",
                "to": [recipient_email],
                "subject": subject,
                "text": body,
            }
            resp = httpx.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in (200, 201):
                print(f"[OTP SERVICE] Email successfully dispatched to {recipient_email} via Resend HTTP API")
                return
            else:
                print(f"[OTP SERVICE] Resend API error ({resp.status_code}): {resp.text}")
        except Exception as exc:
            print(f"[OTP SERVICE] Failed to send email via Resend API: {str(exc)}")

    # 2. Try Brevo HTTP API
    brevo_key = settings.brevo_api_key.strip() if settings.brevo_api_key else ""
    if brevo_key:
        try:
            print("[OTP SERVICE] Sending email via Brevo HTTP API...")
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "api-key": brevo_key,
                "Content-Type": "application/json",
            }
            sender_name = "Swachh PU"
            sender_addr = settings.smtp_user or "monaalmamen@gmail.com"
            if "<" in settings.emails_from and ">" in settings.emails_from:
                sender_name = settings.emails_from.split("<")[0].strip()
                sender_addr = settings.emails_from.split("<")[1].replace(">", "").strip()
            
            payload = {
                "sender": {"name": sender_name, "email": sender_addr},
                "to": [{"email": recipient_email}],
                "subject": subject,
                "textContent": body,
            }
            resp = httpx.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in (200, 201):
                print(f"[OTP SERVICE] Email successfully dispatched to {recipient_email} via Brevo HTTP API")
                return
            else:
                print(f"[OTP SERVICE] Brevo API error ({resp.status_code}): {resp.text}")
        except Exception as exc:
            print(f"[OTP SERVICE] Failed to send email via Brevo API: {str(exc)}")

    # 3. Fallback to SMTP
    smtp_user = settings.smtp_user.strip() if settings.smtp_user else ""
    smtp_password = settings.smtp_password.strip() if settings.smtp_password else ""
    smtp_server = settings.smtp_server.strip() if settings.smtp_server else "smtp.gmail.com"
    smtp_port = int(settings.smtp_port) if settings.smtp_port else 587

    if not smtp_user or not smtp_password:
        print("[OTP SERVICE] SMTP user/password not configured in environment. Skipping actual email sending.")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.emails_from if settings.emails_from else formataddr(("Swachh PU", smtp_user))
    msg["To"] = recipient_email

    ports_to_try = [smtp_port]
    fallback_port = 587 if smtp_port == 465 else 465
    if fallback_port not in ports_to_try:
        ports_to_try.append(fallback_port)

    for port in ports_to_try:
        try:
            print(f"[OTP SERVICE] Attempting to send email via SMTP ({smtp_server}:{port})...")
            if port == 465:
                with smtplib.SMTP_SSL(smtp_server, port, timeout=15) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, [recipient_email], msg.as_string())
            else:
                with smtplib.SMTP(smtp_server, port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, [recipient_email], msg.as_string())
            print(f"[OTP SERVICE] Email successfully dispatched to {recipient_email} via port {port}")
            return
        except Exception as e:
            print(f"[OTP SERVICE] Failed to send email via SMTP ({smtp_server}:{port}): {str(e)}")


async def generate_and_save_otp(user_id: str, email: str = None) -> str:
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

    recipient_email = email
    if not recipient_email:
        user_res = admin.table("users").select("email").eq("id", user_id).execute()
        if user_res.data:
            recipient_email = user_res.data[0].get("email")

    if recipient_email:
        await asyncio.to_thread(send_otp_email, recipient_email, otp_code)

    print(f"==========================================")
    print(f"[OTP SERVICE] Sent OTP {otp_code} to user_id {user_id} ({recipient_email})")
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

    otp_code = await generate_and_save_otp(user["id"], user["email"])
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
