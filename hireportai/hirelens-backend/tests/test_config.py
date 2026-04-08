"""Sanity checks for the post-PG-migration Settings object."""
from app.core.config import Settings, get_settings


def test_database_url_default_is_postgres():
    s = Settings()
    assert s.database_url.startswith("postgresql+asyncpg://"), s.database_url


def test_enable_sqlite_tracker_removed():
    assert not hasattr(Settings(), "enable_sqlite_tracker")
    assert "enable_sqlite_tracker" not in Settings.model_fields


def test_get_settings_cached():
    assert get_settings() is get_settings()
