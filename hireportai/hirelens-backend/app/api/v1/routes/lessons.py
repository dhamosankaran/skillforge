"""Lesson API routes — Phase 6 slice 6.3 (fixture-data, read-only).

Spec: docs/specs/phase-6/03-lesson-ux.md §5.1; slice 6.5
(`docs/specs/phase-6/06-read-time-invariants.md`) §6.4.

  GET /api/v1/lessons/{lesson_id}  Lesson body + ordered quiz items.

Authenticated. Returns 404 for unknown / archived / persona-narrowed
lesson_ids. Returns 403 when the parent deck is premium-tier and the
caller is on the free plan (slice 6.5 §12 D-2 / D-10).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.lesson import LessonWithQuizzesResponse
from app.services import lesson_service, quiz_item_study_service

router = APIRouter()


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonWithQuizzesResponse,
    summary="Get a single lesson with its quiz items",
)
async def get_lesson_route(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonWithQuizzesResponse:
    try:
        bundle = await lesson_service.get_lesson_with_quizzes(
            lesson_id, db, user=user
        )
    except quiz_item_study_service.QuizItemForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )
    return bundle
