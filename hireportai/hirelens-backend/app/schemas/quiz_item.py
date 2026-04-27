"""Pydantic v2 schemas for the Phase 6 `quiz_items` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.3 (slice 6.1) +
docs/specs/phase-6/02-fsrs-quiz-item-binding.md §6 (slice 6.2 — adds
the FSRS daily-review + review-submit + progress wire shapes).
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.study import DailyStatus  # re-imported per spec §6.2

QuizQuestionType = Literal["mcq", "free_text", "code_completion"]
QuizDifficulty = Literal["easy", "medium", "hard"]


class QuizItemResponse(BaseModel):
    """A single quiz item (read shape)."""

    id: str
    lesson_id: str
    question: str
    answer: str
    question_type: QuizQuestionType
    distractors: Optional[list[str]] = None
    difficulty: QuizDifficulty
    display_order: int
    version: int
    superseded_by_id: Optional[str] = None
    retired_at: Optional[datetime] = None
    generated_by_model: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Slice 6.2 — FSRS daily-review wire shapes (spec §6) ─────────────────────


class DailyQuizItem(BaseModel):
    """A single quiz item in the daily review queue (spec 6.2 §6.1).

    `due_date` is None for quiz_items the user has never reviewed
    (state="new"). `reps` and `lapses` are 0 for those same items.
    """

    quiz_item_id: str
    lesson_id: str
    lesson_title: str
    deck_id: str
    deck_slug: str
    question: str
    answer: str
    question_type: QuizQuestionType
    distractors: Optional[list[str]] = None
    difficulty: QuizDifficulty
    fsrs_state: str  # new | learning | review | relearning
    due_date: Optional[datetime] = None
    reps: int
    lapses: int

    model_config = ConfigDict(from_attributes=True)


class DailyQuizReviewResponse(BaseModel):
    """Response for GET /api/v1/quiz-items/daily (spec 6.2 §6.2)."""

    quiz_items: list[DailyQuizItem]
    total_due: int
    session_id: str  # UUID; echo in quiz_review_session_completed event
    daily_status: DailyStatus  # permissive sentinel until wall slice (D-4)


class QuizReviewRequest(BaseModel):
    """Request body for POST /api/v1/quiz-items/review (spec 6.2 §6.3)."""

    quiz_item_id: str
    rating: int = Field(..., ge=1, le=4, description="Again=1, Hard=2, Good=3, Easy=4")
    session_id: str
    time_spent_ms: int = Field(default=0, ge=0, le=300_000)


class QuizReviewResponse(BaseModel):
    """Response for POST /api/v1/quiz-items/review (spec 6.2 §6.4).

    All FSRS values reflect the state AFTER applying the review.
    `scheduled_days` is fractional days from now to `due_date`.
    """

    quiz_item_id: str
    fsrs_state: str  # learning | review | relearning
    stability: float
    difficulty: float
    due_date: datetime
    reps: int
    lapses: int
    scheduled_days: float


class QuizProgressResponse(BaseModel):
    """Response for GET /api/v1/quiz-items/progress (spec 6.2 §6.5)."""

    total_reviewed: int  # quiz_items with at least one review (state != 'new')
    by_state: dict[str, int]  # {"new": n, "learning": n, "review": n, "relearning": n}
    total_reps: int
    total_lapses: int
