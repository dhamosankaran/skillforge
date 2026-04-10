"""Gamification API routes — XP, streaks, badges.

Endpoints:
  GET /gamification/stats   Return the caller's XP, streak, and earned badges.

POST /gamification/award-xp is intentionally NOT exposed here: XP is currently
awarded server-internally from study_service, so an external mutation route
would only enable client tampering. The route stays in the spec for the day a
quiz feature needs to award XP from a different surface.
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import gamification_service

router = APIRouter()


# ── Response schemas ─────────────────────────────────────────────────────────


class BadgeResponse(BaseModel):
    badge_id: str
    name: str
    earned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GamificationStatsResponse(BaseModel):
    user_id: str
    current_streak: int
    longest_streak: int
    total_xp: int
    last_active_date: Optional[date]
    freezes_available: int
    badges: list[BadgeResponse]


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/gamification/stats",
    response_model=GamificationStatsResponse,
    summary="Get the caller's gamification stats",
)
async def get_gamification_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GamificationStatsResponse:
    """Return XP, streak, freezes, and earned badges for the authenticated user.

    Performs a lazy streak-reset on read: if the user missed at least one full
    UTC day since `last_active_date`, the current streak is set to 0 before
    the response is built. Pro freeze logic is handled by the nightly job, not
    here.
    """
    view = await gamification_service.get_stats(user_id=user.id, db=db)
    return GamificationStatsResponse(
        user_id=view.user_id,
        current_streak=view.current_streak,
        longest_streak=view.longest_streak,
        total_xp=view.total_xp,
        last_active_date=view.last_active_date,
        freezes_available=view.freezes_available,
        badges=[BadgeResponse(**b) for b in view.badges],
    )
