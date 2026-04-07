"""Cover letter generation endpoint (v1)."""
from app.api.routes.cover_letter import router  # noqa: F401 — re-export legacy router

__all__ = ["router"]
