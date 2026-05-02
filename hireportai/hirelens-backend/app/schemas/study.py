"""Pydantic v2 schemas for the Study / FSRS endpoints."""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Slice 6.15 / B-102: lifted to its own module. Re-exported here for
# back-compat per §12 D-1 until spec 16 retires `schemas/study.py`.
from app.schemas.daily_status import DailyStatus


class DailyCardItem(BaseModel):
    """A single card in the daily review queue.

    `due_date` is None for cards the user has never reviewed (state="new").
    `reps` and `lapses` are 0 for those same cards.
    """

    card_id: str
    question: str
    answer: str
    difficulty: str
    tags: list[str]
    category_id: str
    category_name: str
    fsrs_state: str  # new | learning | review | relearning
    due_date: Optional[datetime] = None
    reps: int
    lapses: int

    model_config = ConfigDict(from_attributes=True)


class DailyReviewResponse(BaseModel):
    """Response for GET /api/v1/study/daily."""

    cards: list[DailyCardItem]
    total_due: int
    session_id: str  # UUID; echo in daily_review_completed analytics event
    # B-019: True when the caller has already reviewed enough distinct cards
    # today (UTC) that no more "owed" reviews remain. `total_due` still counts
    # the queue length (overdue + fresh-fill) so DailyReview.tsx can render a
    # queue even after completion; this flag lets TodaysReviewWidget flip to
    # its done-state independently of the queue length. Threshold is
    # `reviewed_today >= min(_DAILY_GOAL, available_cards_count)` so a user
    # whose library is smaller than the goal still has a reachable true.
    completed_today: bool = False
    # B-059 / spec #63: pre-flight wall state. Default is the
    # permissive sentinel — old test callers that don't pass `user` to
    # `study_service.get_daily_review` still get a valid payload.
    daily_status: DailyStatus = Field(
        default_factory=lambda: DailyStatus(
            cards_consumed=0,
            cards_limit=-1,
            can_review=True,
            resets_at=datetime(1970, 1, 1, tzinfo=timezone.utc),
        )
    )


class ReviewRequest(BaseModel):
    """Request body for POST /api/v1/study/review."""

    card_id: str
    rating: int = Field(..., ge=1, le=4, description="Again=1, Hard=2, Good=3, Easy=4")
    session_id: str
    time_spent_ms: int = Field(default=0, ge=0, le=300_000)


class ReviewResponse(BaseModel):
    """Response for POST /api/v1/study/review.

    All FSRS values reflect the state AFTER applying the review.
    `scheduled_days` is the interval the scheduler chose for this review,
    expressed as fractional days from now to `due_date`.
    """

    card_id: str
    fsrs_state: str  # learning | review | relearning
    stability: float
    difficulty: float
    due_date: datetime
    reps: int
    lapses: int
    scheduled_days: float


class StudyProgressResponse(BaseModel):
    """Response for GET /api/v1/study/progress — aggregate stats for the caller."""

    total_reviewed: int  # cards with at least one review (state != 'new')
    by_state: dict[str, int]  # {"new": n, "learning": n, "review": n, "relearning": n}
    total_reps: int  # cumulative successful reviews across all cards
    total_lapses: int  # cumulative Again ratings across all cards
