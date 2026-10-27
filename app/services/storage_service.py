"""
Storage service — upload files to Supabase Storage and return public URLs.
"""

import uuid
from datetime import datetime

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings
from app.utils.db import get_db


# Allowed MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/aac", "audio/mp4", "audio/x-m4a"}

# Max file sizes (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_AUDIO_SIZE = 25 * 1024 * 1024   # 25 MB


def _generate_filename(original: str, prefix: str) -> str:
    """Generate a unique filename: prefix/YYYY-MM-DD/uuid.ext"""
    ext = original.rsplit(".", 1)[-1] if "." in original else "bin"
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    unique_id = uuid.uuid4().hex[:12]
    return f"{prefix}/{date_str}/{unique_id}.{ext}"


async def upload_photo(file: UploadFile) -> str:
    """
    Upload a photo to the task-photos bucket.
    Returns the public URL.
    """
    # Validate content type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type '{file.content_type}'. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    # Read file content
    content = await file.read()

    # Validate size
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Max size: {MAX_IMAGE_SIZE // (1024*1024)} MB",
        )

    settings = get_settings()
    admin = get_db()

    file_path = _generate_filename(file.filename or "photo.jpg", "photos")

    try:
        admin.storage.from_(settings.photo_bucket).upload(
            path=file_path,
            file=content,
            file_options={"content-type": file.content_type},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Photo upload failed: {str(exc)}",
        )

    # Get public URL
    public_url = admin.storage.from_(settings.photo_bucket).get_public_url(file_path)

    return public_url


async def upload_audio(file: UploadFile) -> str:
    """
    Upload an audio file to the task-audio bucket.
    Returns the public URL.
    """
    # Validate content type
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audio type '{file.content_type}'. Allowed: {', '.join(ALLOWED_AUDIO_TYPES)}",
        )

    content = await file.read()

    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio too large. Max size: {MAX_AUDIO_SIZE // (1024*1024)} MB",
        )

    settings = get_settings()
    admin = get_db()

    file_path = _generate_filename(file.filename or "audio.mp3", "audio")

    try:
        admin.storage.from_(settings.audio_bucket).upload(
            path=file_path,
            file=content,
            file_options={"content-type": file.content_type},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio upload failed: {str(exc)}",
        )

    public_url = admin.storage.from_(settings.audio_bucket).get_public_url(file_path)

    return public_url
