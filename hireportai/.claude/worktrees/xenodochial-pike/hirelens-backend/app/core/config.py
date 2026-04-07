"""Application configuration using pydantic-settings."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Existing settings ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    allowed_origins: str = "http://localhost:5173,http://localhost:5199"
    enable_sqlite_tracker: bool = True
    max_upload_size_mb: int = 5

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///data/hirelens.db"

    # --- Google OAuth ---
    google_client_id: str = ""
    google_client_secret: str = ""

    # --- JWT ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Stripe ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_enterprise_price_id: str = ""
    frontend_url: str = "http://localhost:5199"

    # --- LLM ---
    llm_provider: str = "gemini"  # "gemini" or "claude"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated origins into a list."""
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB limit to bytes."""
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
