"""Admin-only endpoints."""
from fastapi import APIRouter, Depends

from app.core.deps import require_admin
from app.models.user import User

router = APIRouter()


@router.get("/admin/ping")
async def admin_ping(user: User = Depends(require_admin)):
    """Smoke-test endpoint that confirms the caller has admin role."""
    return {"ok": True, "role": user.role}
