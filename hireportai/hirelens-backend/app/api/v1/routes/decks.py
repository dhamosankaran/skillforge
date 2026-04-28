"""Deck API routes — Phase 6 slice 6.3 (fixture-data, read-only).

Spec: docs/specs/phase-6/03-lesson-ux.md §5.2 + §5.3; slice 6.5
(`docs/specs/phase-6/06-read-time-invariants.md`) §6.4.

  GET /api/v1/decks/{deck_id}          Deck shell.
  GET /api/v1/decks/{deck_id}/lessons  Deck shell + ordered lessons.

Authenticated. Returns 404 for unknown / archived / persona-narrowed
deck_ids. Returns 403 when the deck is premium-tier and the caller is
on the free plan (slice 6.5 §12 D-2 / D-10).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.deck import DeckLessonsResponse, DeckResponse
from app.services import lesson_service, quiz_item_study_service

router = APIRouter()


@router.get(
    "/decks/{deck_id}",
    response_model=DeckResponse,
    summary="Get a single deck",
)
async def get_deck_route(
    deck_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeckResponse:
    try:
        deck = await lesson_service.get_deck_with_meta(deck_id, db, user=user)
    except quiz_item_study_service.QuizItemForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found",
        )
    return deck


@router.get(
    "/decks/{deck_id}/lessons",
    response_model=DeckLessonsResponse,
    summary="Get a deck shell + its ordered lessons",
)
async def list_deck_lessons_route(
    deck_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeckLessonsResponse:
    try:
        bundle = await lesson_service.get_deck_lessons_bundle(
            deck_id, db, user=user
        )
    except quiz_item_study_service.QuizItemForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found",
        )
    return bundle
