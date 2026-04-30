"""Admin ingestion routes (Phase 6 slice 6.10b — B-083b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §6.3 + §11 +
§12 D-8 / D-10 / D-16.

Three endpoints:
    POST /api/v1/admin/ingest                  — enqueue (202)
    GET  /api/v1/admin/ingest/{job_id}         — status poll (200)
    GET  /api/v1/admin/ingest                  — recent list (200)

Auth chain matches the slice 6.4b admin routers — `audit_admin_request`
at the router level (writes one `admin_audit_log` row per HTTP request
per D-16 / AC-17), `require_admin` on each handler.

Rate limit (D-8): per-admin-user 10/hour via a custom slowapi `key_func`
that resolves the authenticated admin's user_id from the request.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import audit_admin_request, get_current_user, require_admin
from app.core.rate_limit import limiter
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.ingestion import IngestionJobCreateRequest, IngestionJobResponse
from app.services import ingestion_service
from app.services.ingestion_errors import (
    IngestionJobNotFoundError,
    IngestionPayloadError,
    R2UploadError,
)

router = APIRouter(dependencies=[Depends(audit_admin_request)])


def _admin_rate_key(request: Request) -> str:
    """Resolve the per-admin slowapi key from the bearer token.

    Per D-8 the rate limit is per-admin-user (admins share dev / prod
    IPs, so slowapi's default IP keying is inappropriate). We decode the
    JWT inline — slowapi runs before our `require_admin` Depends, so we
    can't read `request.state.user`. Falls back to the remote IP if the
    token is missing / invalid; the auth dependency will reject those
    requests with 401 anyway, so the fallback is purely defensive.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        payload = decode_token(token)
        if payload and payload.get("sub"):
            return f"admin:{payload['sub']}"
    client = request.client.host if request.client else "anonymous"
    return f"ip:{client}"


@router.post(
    "/admin/ingest",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/hour", key_func=_admin_rate_key)
async def enqueue_ingestion_route(
    request: Request,
    payload: IngestionJobCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> IngestionJobResponse:
    """Enqueue a new ingestion job (202 Accepted)."""
    try:
        return await ingestion_service.enqueue_ingestion(
            payload, db, admin=user
        )
    except IngestionPayloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    except R2UploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"R2 upload failed: {exc}",
        )


@router.get(
    "/admin/ingest/{job_id}",
    response_model=IngestionJobResponse,
)
async def get_ingestion_job_route(
    job_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> IngestionJobResponse:
    """Status fetch (admin polling per D-10)."""
    del user  # auth side-effect; admin scope intentional
    try:
        return await ingestion_service.get_ingestion_job(job_id, db)
    except IngestionJobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job not found: {job_id}",
        )


@router.get(
    "/admin/ingest",
    response_model=list[IngestionJobResponse],
)
async def list_ingestion_jobs_route(
    limit: int = Query(default=50, ge=1, le=100),
    mine_only: bool = Query(default=False),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[IngestionJobResponse]:
    """List recent ingestion jobs. `mine_only=true` scopes to caller."""
    admin_id = user.id if mine_only else None
    return await ingestion_service.list_recent_ingestion_jobs(
        db, admin_id=admin_id, limit=limit
    )
