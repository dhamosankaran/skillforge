"""Pydantic v2 schemas for the Study / FSRS endpoints."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
