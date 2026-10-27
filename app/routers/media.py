"""
Media router — serves uploaded photos and audio stored in the `media` table.
"""

from fastapi import APIRouter, HTTPException, Response

from app.utils.db import get_db

router = APIRouter(prefix="/media", tags=["Media"])


@router.get("/{bucket}/{path:path}")
async def get_media(bucket: str, path: str):
    """Return an uploaded file. URLs are produced by /upload/photo and /upload/audio."""
    rows = get_db().run(
        "SELECT content_type, data FROM media WHERE bucket = %s AND path = %s",
        [bucket, path],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(
        content=bytes(rows[0]["data"]),
        media_type=rows[0]["content_type"],
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
