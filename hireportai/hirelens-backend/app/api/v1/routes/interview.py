"""Interview prep endpoint (v1)."""
from app.api.routes.interview import router  # noqa: F401 — re-export legacy router

__all__ = ["router"]
