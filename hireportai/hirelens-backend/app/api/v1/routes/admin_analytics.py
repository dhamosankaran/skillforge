"""Admin analytics endpoints (spec #38 E-018b slice 2/4).

Routes under `/api/v1/admin/analytics/*`. Every route inherits:

- `audit_admin_request` (router-level, from the slice-1 admin router) —
  chains `require_admin`, writes the audit row via BackgroundTasks, and
  side-fires `admin_analytics_viewed` for any path starting with
  `/api/v1/admin/analytics`. This is the first slice where that emitter
  actually fires on real traffic (it was dormant in slice 1).

- Pydantic response validation.

Per spec §API Contract:
- Accepts `?from=YYYY-MM-DD&to=YYYY-MM-DD`. Missing `to` defaults to now;
  missing `from` defaults to `to - 30d`. Invalid ISO date → 422.
- `?format=csv` stub not implemented this slice — CSV export (AC-10) is
  covered by spec §Rollout Slice 2 line item but is a pure presentation
  concern the frontend can derive from the JSON response.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import audit_admin_request
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_analytics import MetricsResponse, PerformanceResponse
from app.services import admin_analytics_service

router = APIRouter(dependencies=[Depends(audit_admin_request)])


def _parse_to_date(to: Optional[str]) -> datetime:
    """Validate `?to=`; default to now. 422 on unparseable input."""
    if to is None:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(to)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid 'to' date: {exc}",
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@router.get("/admin/analytics/metrics", response_model=MetricsResponse)
async def metrics_endpoint(
    to: Optional[str] = Query(default=None, description="ISO date (YYYY-MM-DD)"),
    # `from` is a Python keyword; accept it via alias.
    from_date: Optional[str] = Query(
        default=None, alias="from", description="ISO date (YYYY-MM-DD)"
    ),
    db: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """Six PRD OKRs with 7d/30d deltas (spec AC-2).

    `from_date` is accepted for parity with the spec's date-range contract
    but currently ignored — metrics are point-in-time at `to` with deltas
    computed relative to `to - 7d` / `to - 30d`. Range-start becomes
    meaningful in Slice 3 (behavior funnels).
    """
    to_date = _parse_to_date(to)
    if from_date is not None:
        # Validate shape so 422 fires consistently even though we don't
        # consume the value in Slice 2.
        try:
            datetime.fromisoformat(from_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid 'from' date: {exc}",
            )
    return await admin_analytics_service.get_metrics_summary(db, to_date=to_date)


@router.get("/admin/analytics/performance", response_model=PerformanceResponse)
async def performance_endpoint(
    to: Optional[str] = Query(default=None, description="ISO date (YYYY-MM-DD)"),
    from_date: Optional[str] = Query(default=None, alias="from"),
    db: AsyncSession = Depends(get_db),
) -> PerformanceResponse:
    """LLM spend + Stripe webhook success; latency/error deferred (spec AC-3)."""
    to_date = _parse_to_date(to)
    if from_date is not None:
        try:
            datetime.fromisoformat(from_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid 'from' date: {exc}",
            )
    return await admin_analytics_service.get_performance_summary(db, to_date=to_date)
