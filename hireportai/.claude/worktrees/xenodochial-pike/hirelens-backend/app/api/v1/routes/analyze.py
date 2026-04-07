"""Core resume analysis endpoint (v1)."""
from app.api.routes.analyze import router  # noqa: F401 — re-export legacy router

__all__ = ["router"]
