"""Progress analytics API routes — skill radar + activity heatmap.

Endpoints:
  GET /progress/radar    Category mastery breakdown for radar chart.
  GET /progress/heatmap  Daily review counts for activity heatmap.

All endpoints require a valid JWT (via get_current_user).
PostHog events are NOT fired here — these are passive reads.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.progress import HeatmapResponse, RadarResponse
from app.services import progress_service

router = APIRouter()


@router.get(
    "/progress/radar",
    response_model=RadarResponse,
    summary="Category mastery radar data",
)
async def get_radar(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RadarResponse:
    """Return per-category mastery breakdown for the authenticated user.

    Each category includes total_cards, studied count, and mastery_pct
    (percentage of cards in 'review' state). Used to render the skill
    radar / spider chart on the profile page.
    """
    categories = await progress_service.get_category_coverage(user.id, db)
    return RadarResponse(categories=categories)


@router.get(
    "/progress/heatmap",
    response_model=HeatmapResponse,
    summary="Activity heatmap data",
)
async def get_heatmap(
    days: int = Query(default=90, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HeatmapResponse:
    """Return daily review counts for the last N days (default 90).

    Each entry contains the date and the number of card reviews on that
    day. Days with no reviews are included with review_count=0. Results
    are ordered most recent first.
    """
    heatmap = await progress_service.get_activity_heatmap(user.id, days, db)
    return HeatmapResponse(days=heatmap)
