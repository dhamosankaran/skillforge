"""Pydantic v2 schemas for the Phase 6 `lessons` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.2 (slice 6.1) +
docs/specs/phase-6/03-lesson-ux.md §6.2 (slice 6.3 — adds the
lesson-page bundle returned by GET /api/v1/lessons/{id}).
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.quiz_item import QuizItemResponse

LessonVersionType = Literal["initial", "minor_edit", "substantive_edit"]


class LessonResponse(BaseModel):
    """A single lesson (read shape)."""

    id: str
    deck_id: str
    slug: str
    title: str
    concept_md: str
    production_md: str
    examples_md: str
    display_order: int
    version: int
    version_type: LessonVersionType
    published_at: Optional[datetime] = None
    generated_by_model: Optional[str] = None
    source_content_id: Optional[str] = None
    quality_score: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Slice 6.3 — lesson-page bundle (spec §6.2) ──────────────────────────────


class LessonWithQuizzesResponse(BaseModel):
    """Lesson body + ordered list of active quiz items.

    Returned by GET /api/v1/lessons/{lesson_id}. Top-level `deck_*`
    fields are lifted so the FE can render breadcrumbs / back-links
    without a second round-trip.
    """

    lesson: LessonResponse
    quiz_items: list[QuizItemResponse]
    deck_id: str
    deck_slug: str
    deck_title: str

    model_config = ConfigDict(from_attributes=True)
