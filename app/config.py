import os
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    """All environment variables required by the application."""

    model_config = SettingsConfigDict(
        # Allow overriding the .env file path via ENV_FILE environment variable
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    # ── Supabase ──────────────────────────────────────────────
    # Made optional with None defaults to prevent startup crashes
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None  # service role key (bypasses RLS)

    # ── OpenAI ────────────────────────────────────────────────
    openai_api_key: str | None = None

    # ── App ───────────────────────────────────────────────────
    app_name: str = "jobs.ottobon.cloud"
    debug: bool = False
    frontend_url: str = "http://localhost:5173"

    # ── Telegram ──────────────────────────────────────────────
    telegram_bot_token: str | None = None
    telegram_channel_id: str | None = None
    whatsapp_channel_url: str = "https://whatsapp.com/channel/..."
    telegram_channel_url: str = "https://t.me/..."


# Singleton — import this wherever config is needed
settings = Settings()  # type: ignore[call-arg]
