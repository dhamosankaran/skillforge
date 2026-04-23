"""Admin-only endpoints.

Every route in this router is gated by `require_admin` and audited via the
router-level `audit_admin_request` dependency (fire-and-forget write to
`admin_audit_log`, spec #38 E-018a). `audit_admin_request` chains
`require_admin`, so admin routes that still declare their own
`Depends(require_admin)` don't pay the gate twice — FastAPI deduplicates
same-function dependencies within a request.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import audit_admin_request, require_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.admin_audit_log import AdminAuditLog
from app.models.registration_log import RegistrationLog
from app.models.user import User
from app.schemas.admin_card import (
    AdminCardListResponse,
    AdminCardResponse,
    CardCreateRequest,
    CardDraftResponse,
    CardGenerateRequest,
    CardImportResponse,
    CardUpdateRequest,
)
from app.services import ai_card_service, card_admin_service

router = APIRouter(dependencies=[Depends(audit_admin_request)])


class RegistrationLogEntry(BaseModel):
    id: str
    user_id: str
    ip_address: str
    google_email: str
    created_at: str


class RegistrationLogListResponse(BaseModel):
    items: list[RegistrationLogEntry]
    total: int
    page: int
    per_page: int


class AdminAuditLogEntry(BaseModel):
    id: str
    admin_id: str
    route: str
    method: str
    query_params: dict
    ip_address: str
    created_at: str


class AdminAuditLogListResponse(BaseModel):
    items: list[AdminAuditLogEntry]
    total: int
    page: int
    per_page: int


@router.get("/admin/ping")
async def admin_ping(user: User = Depends(require_admin)):
    """Smoke-test endpoint that confirms the caller has admin role."""
    return {"ok": True, "role": user.role}


@router.get("/admin/cards", response_model=AdminCardListResponse)
async def list_cards(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    category_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    tags: Optional[str] = None,
    q: Optional[str] = None,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await card_admin_service.list_cards(
        db, page=page, per_page=per_page,
        category_id=category_id, difficulty=difficulty, tags=tags, q=q,
    )


@router.post(
    "/admin/cards",
    response_model=AdminCardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_card(
    payload: CardCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await card_admin_service.create_card(payload, db)


@router.put("/admin/cards/{card_id}", response_model=AdminCardResponse)
async def update_card(
    card_id: str,
    payload: CardUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await card_admin_service.update_card(card_id, payload, db)


@router.delete("/admin/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await card_admin_service.delete_card(card_id, db)


@router.post("/admin/cards/import", response_model=CardImportResponse)
async def import_cards(
    file: UploadFile = File(...),
    partial: bool = Query(False),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    return await card_admin_service.bulk_import_csv(content, partial, db)


@router.post("/admin/cards/generate", response_model=CardDraftResponse)
@limiter.limit("5/minute")
async def generate_card(
    request: Request,
    payload: CardGenerateRequest,
    user: User = Depends(require_admin),
):
    return ai_card_service.generate_card_draft(payload)


@router.get("/admin/registration-logs", response_model=RegistrationLogListResponse)
async def list_registration_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    ip_address: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List registration logs with optional filters. Admin-only."""
    query = select(RegistrationLog)
    count_query = select(RegistrationLog)

    if ip_address:
        query = query.where(RegistrationLog.ip_address == ip_address)
        count_query = count_query.where(RegistrationLog.ip_address == ip_address)
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(RegistrationLog.created_at >= dt)
            count_query = count_query.where(RegistrationLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(RegistrationLog.created_at <= dt)
            count_query = count_query.where(RegistrationLog.created_at <= dt)
        except ValueError:
            pass

    from sqlalchemy import func
    total_result = await db.execute(
        select(func.count()).select_from(count_query.subquery())
    )
    total = total_result.scalar_one()

    query = query.order_by(RegistrationLog.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    logs = result.scalars().all()

    return RegistrationLogListResponse(
        items=[
            RegistrationLogEntry(
                id=log.id,
                user_id=log.user_id,
                ip_address=log.ip_address,
                google_email=log.google_email,
                created_at=str(log.created_at),
            )
            for log in logs
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/admin/audit", response_model=AdminAuditLogListResponse)
async def list_admin_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    admin_id: Optional[str] = None,
    route: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Paginated audit trail for admin-scoped HTTP requests (spec #38 AC-9)."""
    query = select(AdminAuditLog)
    count_query = select(AdminAuditLog)

    if admin_id:
        query = query.where(AdminAuditLog.admin_id == admin_id)
        count_query = count_query.where(AdminAuditLog.admin_id == admin_id)
    if route:
        query = query.where(AdminAuditLog.route == route)
        count_query = count_query.where(AdminAuditLog.route == route)
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(AdminAuditLog.created_at >= dt)
            count_query = count_query.where(AdminAuditLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(AdminAuditLog.created_at <= dt)
            count_query = count_query.where(AdminAuditLog.created_at <= dt)
        except ValueError:
            pass

    total_result = await db.execute(
        select(func.count()).select_from(count_query.subquery())
    )
    total = total_result.scalar_one()

    query = query.order_by(AdminAuditLog.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    entries = result.scalars().all()

    return AdminAuditLogListResponse(
        items=[
            AdminAuditLogEntry(
                id=entry.id,
                admin_id=entry.admin_id,
                route=entry.route,
                method=entry.method,
                query_params=entry.query_params,
                ip_address=entry.ip_address,
                created_at=str(entry.created_at),
            )
            for entry in entries
        ],
        total=total,
        page=page,
        per_page=per_page,
    )
