"""
Application configuration — loads environment variables via pydantic-settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All config is read from environment variables / .env file."""

    # Supabase connection
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Storage bucket names
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
