"""Admin quiz_item CRUD routes (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §5.9-§5.10.

Quiz_items are sub-resources of lessons. Substantive PATCH retires the
old row + inserts a new `version+1` replacement per §7.4 / D-18; the
PATCH route returns the NEW row's response.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import audit_admin_request, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.quiz_item import (
    AdminQuizItemStatusFilter,
    QuizItemCreateRequest,
    QuizItemResponse,
    QuizItemUpdateRequest,
)
from app.services import quiz_item_admin_service
from app.services.admin_errors import (
    EditClassificationConflictError,
    LessonArchivedError,
    LessonNotFoundError,
    QuizItemNotFoundError,
)

router = APIRouter(dependencies=[Depends(audit_admin_request)])


class QuizItemRetireRequest(BaseModel):
    superseded_by_id: Optional[str] = None


@router.post(
    "/admin/lessons/{lesson_id}/quiz-items",
    response_model=QuizItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_quiz_item_route(
    lesson_id: str,
    payload: QuizItemCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> QuizItemResponse:
    try:
        return await quiz_item_admin_service.create_quiz_item(
            lesson_id, payload, db, user.id
        )
    except LessonNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )
    except LessonArchivedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot author quiz items on an archived lesson",
        )


@router.get(
    "/admin/lessons/{lesson_id}/quiz-items",
    response_model=list[QuizItemResponse],
)
async def list_admin_quiz_items_route(
    lesson_id: str,
    status_filter: AdminQuizItemStatusFilter = Query(
        default="active", alias="status", description="active | retired | all"
    ),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[QuizItemResponse]:
    del user
    try:
        return await quiz_item_admin_service.list_admin_quiz_items(
            lesson_id, db, status_filter=status_filter
        )
    except LessonNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )


@router.patch(
    "/admin/quiz-items/{quiz_item_id}", response_model=QuizItemResponse
)
async def update_quiz_item_route(
    quiz_item_id: str,
    payload: QuizItemUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> QuizItemResponse:
    try:
        return await quiz_item_admin_service.update_quiz_item(
            quiz_item_id, payload, db, user.id
        )
    except QuizItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz item not found"
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
    "/admin/quiz-items/{quiz_item_id}/retire", response_model=QuizItemResponse
)
async def retire_quiz_item_route(
    quiz_item_id: str,
    payload: QuizItemRetireRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> QuizItemResponse:
    try:
        return await quiz_item_admin_service.retire_quiz_item(
            quiz_item_id, db, user.id, superseded_by_id=payload.superseded_by_id
        )
    except QuizItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz item not found"
        )
