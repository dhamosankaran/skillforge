"""Home dashboard routes — state-aware response (P5-S18c, spec #40)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.home import HomeStateResponse
from app.services import home_state_service

router = APIRouter()


@router.get(
    "/home/state",
    response_model=HomeStateResponse,
    summary="Evaluate the caller's home-page state",
)
async def get_home_state(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeStateResponse:
    """Return priority-ordered active states + context for the home dashboard.

    See spec ``docs/specs/phase-5/40-home-dashboard-state-aware.md`` for the
    full state catalog, priority rules, and caching strategy.
    """
    return await home_state_service.evaluate_state(user=user, db=db)
