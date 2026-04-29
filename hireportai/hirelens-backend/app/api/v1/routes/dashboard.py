"""User-self FSRS dashboard route — Phase 6 slice 6.8.

Spec: docs/specs/phase-6/09-fsrs-dashboard.md §6.2 + §12 D-1 / D-3 /
D-10 / D-14.

  GET /api/v1/learn/dashboard
    Auth: Depends(get_current_user)
    Query: ?retention_window_days=N (default 30 per D-7, range [1, 365])
    Returns: DashboardResponse
    Errors: 401 (no auth), 422 (out-of-range query param)

D-3 single envelope, D-10 free-allowed page (no PaywallTrigger; the
visibility filter chain inside the service hides premium-deck rows
for free users automatically).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard_service

router = APIRouter()


@router.get(
    "/learn/dashboard",
    response_model=DashboardResponse,
    summary="User-self FSRS dashboard (Phase-6 progress aggregator)",
)
async def get_fsrs_dashboard(
    retention_window_days: int = Query(
        default=dashboard_service.DEFAULT_RETENTION_WINDOW_DAYS,
        ge=1,
        le=365,
        description="Days of recent quiz_review_events to aggregate for retention curve.",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Return the dashboard envelope for the authenticated user.

    Cold-start (no progress rows + no events in window) returns
    ``is_cold_start=True`` with zeroed sections — the FE renders
    per-section cold-start variants per §12 D-13.
    """
    return await dashboard_service.aggregate_user_dashboard(
        user,
        db,
        retention_window_days=retention_window_days,
    )
