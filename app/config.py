"""
Application configuration loaded from environment variables.
Uses pydantic-settings for typed, validated config.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    """All environment variables required by the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Supabase ──────────────────────────────────────────────
    supabase_url: str
    supabase_key: str                # anon key (client-facing)
    supabase_service_role_key: str   # service role key (bypasses RLS)
    supabase_jwt_secret: str

    # ── OpenAI ────────────────────────────────────────────────
    openai_api_key: str

    # ── App ───────────────────────────────────────────────────
    app_name: str = "jobs.ottobon.cloud"
    debug: bool = False
    frontend_url: str = "http://localhost:5173"

    # ── Channels ──────────────────────────────────────────────
    whatsapp_channel_url: str = "https://whatsapp.com/channel/..."

    # ── Telegram Channel Broadcast ────────────────────────────
    telegram_bot_token: str | None = None
    telegram_channel_id: str | None = None

    # ── Microsoft Graph ───────────────────────────────────────
    msgraph_client_id: str = "placeholder_client_id"
    msgraph_client_secret: str = "placeholder_secret"
    msgraph_tenant_id: str = "placeholder_tenant"
    msgraph_user_id: str = "placeholder_user"
    onedrive_folder: str = "rag_docs"

    # ── Database & Celery ─────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/jobs_db"
    celery_broker_url: str = "redis://localhost:6379/0"


# Singleton — import this wherever config is needed
settings = Settings()  # type: ignore[call-arg]
