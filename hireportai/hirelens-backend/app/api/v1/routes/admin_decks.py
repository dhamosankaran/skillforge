"""Admin deck CRUD routes (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §5.1-§5.4.

Every route inherits the `audit_admin_request` chain (which itself
chains `require_admin`) per D-7.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import audit_admin_request, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.deck import (
    AdminDeckStatusFilter,
    DeckCreateRequest,
    DeckResponse,
    DeckUpdateRequest,
)
from app.services import deck_admin_service
from app.services.admin_errors import DeckNotFoundError, DeckSlugConflictError

router = APIRouter(dependencies=[Depends(audit_admin_request)])


@router.post(
    "/admin/decks",
    response_model=DeckResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_deck_route(
    payload: DeckCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DeckResponse:
    try:
        return await deck_admin_service.create_deck(payload, db, user.id)
    except DeckSlugConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deck slug already exists: {exc}",
        )


@router.patch("/admin/decks/{deck_id}", response_model=DeckResponse)
async def update_deck_route(
    deck_id: str,
    payload: DeckUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DeckResponse:
    try:
        return await deck_admin_service.update_deck(deck_id, payload, db, user.id)
    except DeckNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found"
        )
    except DeckSlugConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deck slug already exists: {exc}",
        )


@router.post("/admin/decks/{deck_id}/archive", response_model=DeckResponse)
async def archive_deck_route(
    deck_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DeckResponse:
    try:
        return await deck_admin_service.archive_deck(deck_id, db, user.id)
    except DeckNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found"
        )


@router.get("/admin/decks", response_model=list[DeckResponse])
async def list_admin_decks_route(
    status_filter: AdminDeckStatusFilter = Query(
        default="active", alias="status", description="active | archived | all"
    ),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[DeckResponse]:
    del user
    return await deck_admin_service.list_admin_decks(db, status_filter=status_filter)
