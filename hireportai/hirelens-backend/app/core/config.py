"""Application configuration using pydantic-settings."""
from functools import lru_cache
from typing import FrozenSet, List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Existing settings ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    allowed_origins: str = "http://localhost:5173,http://localhost:5199"
    max_upload_size_mb: int = 5

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport"
    )

    # --- Google OAuth ---
    google_client_id: str = ""
    google_client_secret: str = ""

    # --- JWT ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Redis ---
    redis_url: str = "redis://localhost:6379"

    # --- Stripe ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_pro_price_id_inr: str = ""
    stripe_enterprise_price_id: str = ""
    frontend_url: str = "http://localhost:5199"

    # --- Analytics ---
    posthog_api_key: str = ""
    posthog_host: str = "https://us.i.posthog.com"

    # --- LLM ---
    llm_provider: str = "gemini"  # "gemini" or "claude"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # --- LLM Router (multi-model) ---
    llm_fast_provider: str = "gemini"
    llm_fast_model: str = "gemini-2.5-flash"
    llm_reasoning_provider: str = "gemini"
    llm_reasoning_model: str = "gemini-2.5-pro"
    openai_api_key: str = ""

    # --- Error monitoring (Sentry) ---
    sentry_dsn: str = ""

    # --- Email (Resend) ---
    resend_api_key: str = ""
    resend_from_address: str = "reminders@skillforge.app"

    # --- Admin access (spec #54 / E-040) ---
    admin_emails: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        """Return a database URL with the postgresql+asyncpg:// scheme.

        Railway injects DATABASE_URL as postgres:// or postgresql:// (no driver
        prefix). asyncpg requires the +asyncpg driver qualifier, and the legacy
        'postgres://' alias is not accepted. This property normalises all three
        forms so local dev and Railway both work without code changes.
        """
        url = self.database_url
        # Normalise legacy 'postgres://' alias first.
        url = url.replace("postgres://", "postgresql://", 1)
        if not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated origins into a list."""
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB limit to bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def admin_emails_set(self) -> FrozenSet[str]:
        """Parse ADMIN_EMAILS into a lowercase, whitespace-stripped frozenset.

        Empty / missing env var produces an empty frozenset, which fails
        closed in the login-time role-reconciliation path (no user is
        admin). Spec #54 / E-040.
        """
        return frozenset(
            e.strip().lower()
            for e in self.admin_emails.split(",")
            if e.strip()
        )


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
