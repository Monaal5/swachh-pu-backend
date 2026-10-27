"""
Application configuration — loads environment variables via pydantic-settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All config is read from environment variables / .env file."""

    # PostgreSQL connection string (Neon: use the "Pooled connection" URL)
    database_url: str

    # Public URL of this API, used to build links to uploaded media.
    # Optional on Vercel (derived from VERCEL_PROJECT_PRODUCTION_URL).
    public_base_url: str = ""

    # Media bucket names (photos / audio are stored in the `media` table)
    photo_bucket: str = "task-photos"
    audio_bucket: str = "task-audio"

    # SMTP Email configuration
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    emails_from: str = ""

    # Server
    app_title: str = "Swachh PU Backend"
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (parsed once on first call)."""
    return Settings()
