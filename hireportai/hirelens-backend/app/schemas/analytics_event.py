"""Pydantic v2 write-only schemas for the Phase 6 analytics event tables.

Spec: docs/specs/phase-6/00-analytics-tables.md §5.

`reviewed_at` / `viewed_at` are server-set via Postgres `func.now()` and are
not part of the write schema.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class QuizReviewEventCreate(BaseModel):
    """Service-layer payload for `analytics_event_service.write_quiz_review_event`."""

    user_id: Optional[str] = None
    quiz_item_id: str
    lesson_id: str
    deck_id: str
    rating: int = Field(..., ge=1, le=4)
    fsrs_state_before: Literal["new", "learning", "review", "relearning"]
    fsrs_state_after: Literal["new", "learning", "review", "relearning"]
    reps: int = Field(..., ge=0)
    lapses: int = Field(..., ge=0)
    time_spent_ms: int = Field(default=0, ge=0)
    session_id: Optional[str] = None
    plan: Optional[Literal["free", "pro", "enterprise"]] = None
    persona: Optional[
        Literal["interview_prepper", "career_climber", "team_lead"]
    ] = None


class LessonViewEventCreate(BaseModel):
    """Service-layer payload for `analytics_event_service.write_lesson_view_event`."""

    user_id: Optional[str] = None
    lesson_id: str
    deck_id: str
    version: int = Field(..., ge=1)
    session_id: Optional[str] = None
    plan: Optional[Literal["free", "pro", "enterprise"]] = None
    persona: Optional[
        Literal["interview_prepper", "career_climber", "team_lead"]
    ] = None


class LessonViewEventRequest(BaseModel):
    """Request body for `POST /api/v1/lessons/{lesson_id}/view-event`.

    Server-derived fields (`user_id`, `plan`, `persona`) are NOT
    client-supplied — the route resolves them from `Depends(get_current_user)`
    + subscription state. `lesson_id` is the URL path param.
    """

    deck_id: str
    version: int = Field(..., ge=1)
    session_id: Optional[str] = None
