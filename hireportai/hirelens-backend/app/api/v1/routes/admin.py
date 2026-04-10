"""Admin-only endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_card import (
    AdminCardListResponse,
    AdminCardResponse,
    CardCreateRequest,
    CardImportResponse,
    CardUpdateRequest,
)
from app.services import card_admin_service

router = APIRouter()


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
