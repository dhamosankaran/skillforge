"""AppShell loop-progress route — Phase 5 spec #66 / E-051.

  GET /api/v1/learn/loop-progress?tracker_id=<uuid>
    Auth: Depends(get_current_user)
    Returns: LoopProgressResponse
    Errors: 401 (no auth), 404 (tracker not found or cross-user),
            422 (missing/malformed query param)

D-13 LOCKED — flat path under `/learn` namespace; matches `/learn/dashboard`
precedent (spec #09). Query param `tracker_id` chosen over RESTful nesting
to keep parity with the existing `useScoreHistory` shape.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.loop_progress import LoopProgressResponse
from app.services.loop_progress_service import (
    TrackerNotFoundError,
    get_loop_progress,
)

router = APIRouter()


@router.get(
    "/learn/loop-progress",
    response_model=LoopProgressResponse,
    summary="Per-tracker gap-card review progress for the AppShell loop strip",
)
async def loop_progress_route(
    tracker_id: str = Query(..., description="Tracker application id."),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoopProgressResponse:
    """Return loop-progress for the given tracker (404 if cross-user)."""
    try:
        return await get_loop_progress(db, user.id, tracker_id)
    except TrackerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracker application not found.",
        )
