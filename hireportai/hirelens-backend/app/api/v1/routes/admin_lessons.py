"""Admin lesson CRUD routes (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §5.5-§5.8.

Includes the deck-scoped POST/GET (`/admin/decks/{deck_id}/lessons`)
because lessons live under a deck per the URL hierarchy.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import audit_admin_request, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.lesson import (
    AdminLessonStatusFilter,
    LessonCreateRequest,
    LessonResponse,
    LessonUpdateRequest,
    LessonUpdateResponse,
)
from app.services import lesson_admin_service
from app.services.admin_errors import (
    DeckNotFoundError,
    EditClassificationConflictError,
    LessonArchivedError,
    LessonNotFoundError,
    LessonSlugConflictError,
)

router = APIRouter(dependencies=[Depends(audit_admin_request)])


@router.post(
    "/admin/decks/{deck_id}/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson_route(
    deck_id: str,
    payload: LessonCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> LessonResponse:
    try:
        return await lesson_admin_service.create_lesson(
            deck_id, payload, db, user.id
        )
    except DeckNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found"
        )
    except LessonSlugConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lesson slug already exists in deck: {exc}",
        )


@router.get(
    "/admin/decks/{deck_id}/lessons", response_model=list[LessonResponse]
)
async def list_admin_lessons_route(
    deck_id: str,
    status_filter: AdminLessonStatusFilter = Query(
        default="active",
        alias="status",
        description="active | drafts | published | archived | all",
    ),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[LessonResponse]:
    del user
    try:
        return await lesson_admin_service.list_admin_lessons(
            deck_id, db, status_filter=status_filter
        )
    except DeckNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found"
        )


@router.patch(
    "/admin/lessons/{lesson_id}", response_model=LessonUpdateResponse
)
async def update_lesson_route(
    lesson_id: str,
    payload: LessonUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> LessonUpdateResponse:
    try:
        return await lesson_admin_service.update_lesson(
            lesson_id, payload, db, user.id
        )
    except LessonNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )
    except LessonSlugConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lesson slug already exists in deck: {exc}",
        )
    except EditClassificationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "edit_classification_mismatch",
                "expected": exc.expected,
                "claimed": exc.claimed,
                "fields": exc.fields,
            },
        )


@router.post(
    "/admin/lessons/{lesson_id}/publish", response_model=LessonResponse
)
async def publish_lesson_route(
    lesson_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> LessonResponse:
    try:
        return await lesson_admin_service.publish_lesson(lesson_id, db, user.id)
    except LessonNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )
    except LessonArchivedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot publish an archived lesson",
        )


@router.post(
    "/admin/lessons/{lesson_id}/archive", response_model=LessonResponse
)
async def archive_lesson_route(
    lesson_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> LessonResponse:
    try:
        return await lesson_admin_service.archive_lesson(lesson_id, db, user.id)
    except LessonNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )
