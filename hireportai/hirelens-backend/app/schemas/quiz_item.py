"""Pydantic v2 schemas for the Phase 6 `quiz_items` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.3.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

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
