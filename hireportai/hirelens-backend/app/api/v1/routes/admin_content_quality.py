"""Admin content-quality dashboard route — Phase 6 slice 6.11.

Spec: docs/specs/phase-6/11-content-quality-retention.md §6.2 +
§11 AC-1..AC-3 / AC-10 / AC-16 + §12 D-6 / D-12 / D-16.

One endpoint:
    GET /api/v1/admin/content-quality

Auth chain matches the slice 6.4b / 6.10 admin routers —
``audit_admin_request`` at the router level (writes one
``admin_audit_log`` row per HTTP request per AC-16) chains
``require_admin``, so unauthed → 401 and non-admin → 403 reach the
client without the service running. Plain ``Depends(require_admin)``
per D-12 (no sub-permission introduced).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import audit_admin_request, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_content_quality import AdminContentQualityResponse
from app.services.admin_content_quality_service import (
    MAX_WINDOW_DAYS,
    MIN_WINDOW_DAYS,
    aggregate_dashboard,
)

router = APIRouter(dependencies=[Depends(audit_admin_request)])


@router.get(
    "/admin/content-quality",
    response_model=AdminContentQualityResponse,
)
async def get_content_quality_route(
    window_days: int = Query(default=30, ge=MIN_WINDOW_DAYS, le=MAX_WINDOW_DAYS),
    include_archived: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> AdminContentQualityResponse:
    """Single-envelope admin content-quality dashboard (D-6)."""
    del user  # auth side-effect; admin scope intentional
    return await aggregate_dashboard(
        db,
        window_days=window_days,
        include_archived=include_archived,
    )
