"""User-thumbs route — Phase 6 slice 6.13.5b.

Spec: docs/specs/phase-6/12-quality-signals.md §6.4 + §11 AC-5..AC-8.

  POST /api/v1/lessons/{lesson_id}/thumbs   user-thumbs submission

Auth-gated per §12 D-10 (no anonymous thumbs). Score validator rejects
values outside {-1, +1} per §12 D-11 + AC-8 — no clear-thumbs path v1.
Lesson-level only per §12 D-7 (no per-quiz_item route v1).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.card_quality_signal import ThumbsRequest, ThumbsResponse
from app.services import thumbs_service
from app.services.quiz_item_study_service import QuizItemForbiddenError

router = APIRouter()


@router.post(
    "/lessons/{lesson_id}/thumbs",
    response_model=ThumbsResponse,
    summary="Submit a user-thumbs vote on a lesson",
)
async def submit_lesson_thumbs(
    lesson_id: str,
    payload: ThumbsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThumbsResponse:
    try:
        return await thumbs_service.submit_thumbs(
            lesson_id=lesson_id,
            score=payload.score,
            user=user,
            db=db,
        )
    except thumbs_service.LessonNotVisibleError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )
    except QuizItemForbiddenError as exc:
        # Re-raised by lesson_service.get_lesson_with_quizzes when the
        # parent deck is premium-tier and the user is on the free plan
        # (slice 6.5 §12 D-2 / D-10). Mirrors lessons.py route behavior.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
