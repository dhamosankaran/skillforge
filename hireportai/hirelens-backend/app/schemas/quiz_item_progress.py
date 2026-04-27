"""Pydantic v2 schemas for the Phase 6 `quiz_item_progress` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.4. Schema mirrors
`card_progress` modulo the FK swap (D-1, AC-6).
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

FsrsState = Literal["new", "learning", "review", "relearning"]


class QuizItemProgressResponse(BaseModel):
    """A single user × quiz_item FSRS progress row (read shape)."""

    id: str
    user_id: str
    quiz_item_id: str
    state: FsrsState
    stability: float
    difficulty_fsrs: float
    elapsed_days: float
    scheduled_days: float
    reps: int
    lapses: int
    fsrs_step: Optional[int] = None
    last_reviewed: Optional[datetime] = None
    due_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
