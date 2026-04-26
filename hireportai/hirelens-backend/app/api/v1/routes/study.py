"""Study API routes — FSRS spaced-repetition daily review.

Endpoints:
  GET  /study/daily      Return up to 5 cards due for review today.
  POST /study/review     Submit a review rating; advance FSRS state.
  GET  /study/progress   Return aggregate study statistics.
  POST /study/experience Generate AI experience narrative from study history.

All endpoints require a valid JWT (via get_current_user).
Plan-gate enforcement (free vs pro) is computed here and forwarded to
the service layer as a plain bool so the service stays testable without
full User objects.

PostHog events are fired inside the service; the route stays thin.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.study import DailyReviewResponse, ReviewRequest, ReviewResponse, StudyProgressResponse
from app.services import experience_service, study_service

router = APIRouter()


# ── Plan gate helper ──────────────────────────────────────────────────────────


def _is_free(user: User) -> bool:
    """Return True when the user is on the free plan (or has no active subscription).

    Matches the same logic used in card_service._is_free so plan-gate
    behaviour is consistent across all content-serving endpoints.
    """
    sub = user.subscription  # loaded via selectin by get_current_user
    if sub is None:
        return True
    if sub.status != "active":
        return True
    return sub.plan == "free"


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/study/daily",
    response_model=DailyReviewResponse,
    summary="Get today's due cards",
)
async def get_daily_review(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DailyReviewResponse:
    """Return up to 5 cards due for review for the authenticated user.

    Queue is built in two passes:
      1. Overdue progress rows (due_date <= now), ordered by due_date ASC.
      2. Unreviewed cards (no progress row) fill any remaining slots up to 5.

    Free-plan users only see cards from `source='foundation'` categories.
    Returns an empty list (never 404) when nothing is due.
    """
    return await study_service.get_daily_review(
        user_id=user.id,
        is_free=_is_free(user),
        db=db,
        user=user,
    )


@router.post(
    "/study/review",
    response_model=ReviewResponse,
    summary="Submit a card review rating",
)
async def submit_review(
    body: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Submit a review rating for a single card.

    Creates a card_progress row on first review; updates it on subsequent
    reviews. The FSRS scheduler computes the next due date server-side.

    Rating values: Again=1, Hard=2, Good=3, Easy=4.

    Error responses:
      400 — rating outside [1, 4] or time_spent_ms outside [0, 300 000]
      402 — free user hit the daily 10-card review wall (spec #50)
      403 — card exists but is in a category the caller's plan does not permit
      404 — no card with the given card_id
    """
    try:
        return await study_service.review_card(
            user_id=user.id,
            card_id=body.card_id,
            rating=body.rating,
            is_free=_is_free(user),
            db=db,
            time_spent_ms=body.time_spent_ms,
            session_id=body.session_id,
            user=user,
        )
    except study_service.CardNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except study_service.CardForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except study_service.DailyReviewLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=exc.payload,
        )


@router.get(
    "/study/progress",
    response_model=StudyProgressResponse,
    summary="Get overall study progress",
)
async def get_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudyProgressResponse:
    """Return aggregate study statistics for the authenticated user.

    Counts card_progress rows by FSRS state (learning / review / relearning)
    and totals reps and lapses. Cards the user has never touched are not
    included in the counts (they appear as 'unreviewed' in the daily queue).
    """
    return await study_service.get_progress(user_id=user.id, db=db)


# ── Experience generation ────────────────────────────────────────────────────


class ExperienceRequest(BaseModel):
    topic: Optional[str] = None


class ExperienceResponse(BaseModel):
    experience_text: str
    summary: str
    cards_studied: int


@router.post(
    "/study/experience",
    response_model=ExperienceResponse,
    summary="Generate AI experience narrative",
)
async def generate_experience(
    body: ExperienceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExperienceResponse:
    """Generate a resume-ready bullet point from the user's study history.

    Uses the configured LLM provider to turn study stats into a
    professional narrative suitable for a resume or LinkedIn profile.
    """
    result = await experience_service.generate_experience(
        user_id=user.id,
        topic=body.topic or "",
        db=db,
    )
    return ExperienceResponse(**result)
