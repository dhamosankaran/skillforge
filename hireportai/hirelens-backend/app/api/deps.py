"""Backward-compat shim — imports moved to app.core.deps."""
from app.core.deps import verify_content_length  # noqa: F401

__all__ = ["verify_content_length"]
