"""Quiz-item API routes — Phase 6 FSRS spaced-repetition daily review.

Endpoints (spec docs/specs/phase-6/02-fsrs-quiz-item-binding.md §5):
  GET  /quiz-items/daily     Up to 5 quiz_items due today.
  POST /quiz-items/review    Submit a review rating; advance FSRS state.
  GET  /quiz-items/progress  Aggregate study stats.

All endpoints require a valid JWT (via get_current_user). PostHog
events fire from the service layer — routes stay thin.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.quiz_item import (
    DailyQuizReviewResponse,
    QuizProgressResponse,
    QuizReviewRequest,
    QuizReviewResponse,
)
from app.services import quiz_item_study_service

router = APIRouter()


@router.get(
    "/quiz-items/daily",
    response_model=DailyQuizReviewResponse,
    summary="Get today's due quiz items",
)
async def get_daily_quiz_items(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DailyQuizReviewResponse:
    """Return up to 5 quiz_items due for review.

    Two-pass queue: overdue (due_date <= now, ordered ASC) then fill
    with unreviewed quiz_items. Excludes retired quiz_items, archived
    lessons, and archived decks. Returns an empty list (never 404)
    when nothing is due.

    `daily_status` is the permissive sentinel until the wall-enforcement
    slice lands (spec D-4).
    """
    return await quiz_item_study_service.get_daily_quiz_items(
        user_id=user.id,
        db=db,
        user=user,
    )


@router.post(
    "/quiz-items/review",
    response_model=QuizReviewResponse,
    summary="Submit a quiz item review rating",
)
async def submit_quiz_review(
    body: QuizReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizReviewResponse:
    """Submit a review rating for a single quiz_item.

    Rating values: Again=1, Hard=2, Good=3, Easy=4.

    Error responses:
      400 — rating outside [1, 4] or time_spent_ms outside [0, 300_000]
      403 — quiz_item is in an archived lesson or deck OR the parent
            deck is premium-tier and the caller is on the free plan
            (slice 6.5 §12 D-2)
      404 — no quiz_item with the given quiz_item_id, OR the parent
            deck is not visible to the caller's persona (slice 6.5
            §12 D-7)
      409 — quiz_item is retired and no existing progress row (new
            reviews blocked; updates to existing rows pass through)
    """
    try:
        return await quiz_item_study_service.review_quiz_item(
            user_id=user.id,
            quiz_item_id=body.quiz_item_id,
            rating=body.rating,
            db=db,
            time_spent_ms=body.time_spent_ms,
            session_id=body.session_id,
            user=user,
        )
    except quiz_item_study_service.QuizItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except quiz_item_study_service.QuizItemNotVisibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except quiz_item_study_service.QuizItemForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except quiz_item_study_service.QuizItemRetiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get(
    "/quiz-items/progress",
    response_model=QuizProgressResponse,
    summary="Get overall quiz-item study progress",
)
async def get_quiz_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizProgressResponse:
    """Return aggregate study statistics for the authenticated user.

    Counts quiz_item_progress rows by FSRS state and totals reps and
    lapses. Quiz items the user has never touched are not in the counts
    (they appear as fresh-fill in the daily queue).
    """
    return await quiz_item_study_service.get_quiz_progress(
        user_id=user.id, db=db
    )
