"""
Application settings.

All environment variables are read from the .env file via pydantic-settings.
Import the `settings` singleton anywhere in the app:

    from app.config import settings
    print(settings.database_url)

Never hardcode secrets — always use settings.<field>.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Typed application settings loaded from environment variables.

    pydantic-settings automatically reads these from:
      1. Environment variables (e.g. export DATABASE_URL=...)
      2. A .env file in the working directory (loaded by python-dotenv)

    Field names are case-insensitive: DATABASE_URL → database_url.
    """

    model_config = SettingsConfigDict(
        env_file=".env",           # path to the .env file
        env_file_encoding="utf-8",
        case_sensitive=False,      # DATABASE_URL and database_url both work
        extra="ignore",            # silently ignore unknown env vars
    )

    # ── Database ──────────────────────────────────────────────────────────────
    # asyncpg connection string, e.g.:
    #   postgresql+asyncpg://user:password@localhost:5432/spent
    # Railway provides DATABASE_URL as postgres:// or postgresql:// — the
    # validator below normalizes it to the asyncpg driver format automatically.
    database_url: str

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        """Normalize Railway's postgres:// URL to the asyncpg driver format."""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # ── Anthropic AI (Phase 3) ────────────────────────────────────────────────
    # Used by services/ai.py to call Claude for expense categorization.
    anthropic_api_key: str = ""

    # ── Telegram Bot (Phase 2) ────────────────────────────────────────────────
    telegram_bot_token: str = ""

    # Comma-separated Telegram user IDs. The bot only answers these users, and
    # the backend sends auto-logged purchase notifications to them.
    telegram_allowed_user_ids: str = ""

    @property
    def telegram_owner_ids(self) -> list[int]:
        """Return TELEGRAM_ALLOWED_USER_IDS parsed into a list of ints."""
        return [int(uid) for uid in self.telegram_allowed_user_ids.split(",") if uid.strip()]

    # ── AI Settings (Phase 3) ─────────────────────────────────────────────────
    # Confidence threshold below which we fall back to category="other".
    ai_confidence_threshold: float = 0.75

    # ── API Auth ──────────────────────────────────────────────────────────────
    # Shared secret required as "Authorization: Bearer <token>" on every
    # /api/v1 request. Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    # If unset, the API is open in development and refuses all requests in production.
    api_token: str = ""

    # ── App ───────────────────────────────────────────────────────────────────
    # Controls SQL echo logging and debug behavior.
    # Values: "development" | "production"
    environment: str = "development"

    @property
    def is_development(self) -> bool:
        """Return True when running in development mode."""
        return self.environment == "development"


# Module-level singleton — import this everywhere instead of instantiating Settings() again.
settings = Settings()
