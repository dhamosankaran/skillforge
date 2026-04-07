"""Resume rewrite endpoint (v1)."""
from app.api.routes.rewrite import router  # noqa: F401 — re-export legacy router

__all__ = ["router"]
