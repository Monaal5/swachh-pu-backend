"""
Swachh PU Backend — FastAPI Application Entry Point

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import psycopg
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, admin, profiles, tasks, upload, locations, media
from app.utils.db import get_db

settings = get_settings()

# ── App Initialisation ───────────────────────────────────────

app = FastAPI(
    title=settings.app_title,
    description=(
        "Backend API for Swachh PU Abhiyaan — campus cleanliness task management.\n\n"
        "**Roles**: student, faculty, worker, admin\n\n"
        "**Features**: Multi-role signup, Email OTP verification, Master Worker verification, Admin verification workflow."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (allow Flutter app / any frontend) ──────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Bad IDs / values from the client → 400 instead of 500 ──

@app.exception_handler(psycopg.errors.DataError)
async def data_error_handler(request: Request, exc: psycopg.errors.DataError):
    return JSONResponse(status_code=400, content={"detail": "Invalid value in request (for example a malformed ID)."})


# ── Register Routers ─────────────────────────────────────────

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(profiles.router)
app.include_router(profiles.workers_router)
app.include_router(tasks.router)
app.include_router(upload.router)
app.include_router(locations.router)
app.include_router(media.router)


# ── Health Check ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_title,
        "version": "2.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check (includes a database round-trip)."""
    try:
        get_db().run("SELECT 1")
        database = "connected"
    except Exception as exc:  # report, don't crash the health check
        database = f"error: {type(exc).__name__}"
    return {
        "status": "healthy" if database == "connected" else "degraded",
        "database": database,
        "storage_buckets": {
            "photos": settings.photo_bucket,
            "audio": settings.audio_bucket,
        },
    }
