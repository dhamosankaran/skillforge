"""Backward-compat shim — imports moved to app.core.config."""
from app.core.config import Settings, get_settings  # noqa: F401

__all__ = ["Settings", "get_settings"]
