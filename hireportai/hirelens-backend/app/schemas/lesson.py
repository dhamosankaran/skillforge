"""Pydantic v2 schemas for the Phase 6 `lessons` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.2 (slice 6.1) +
docs/specs/phase-6/03-lesson-ux.md §6.2 (slice 6.3 — adds the
lesson-page bundle returned by GET /api/v1/lessons/{id}) +
docs/specs/phase-6/04-admin-authoring.md §6.4 + §6.5 + §6.6 (slice
6.4b — admin write schemas + cascade-outcome surface).
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.card_quality_signal import ThumbsResponse
from app.schemas.quiz_item import QuizItemResponse

LessonVersionType = Literal["initial", "minor_edit", "substantive_edit"]
# Slice 6.4b D-10 — single Literal alias shared across lesson + quiz_item PATCH.
EditClassification = Literal["minor", "substantive"]
AdminLessonStatusFilter = Literal["active", "drafts", "published", "archived", "all"]

_SLUG_PATTERN = r"^[a-z0-9-]+$"


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
    # Slice 6.13.5b §12 D-12 — single-fetch user-thumbs initial state.
    # Null when the requesting user has not submitted a thumbs for this
    # lesson (FE renders ``<ThumbsControl />`` in unselected state).
    viewer_thumbs: Optional[ThumbsResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ── Slice 6.4b — admin write schemas (spec §6.4 + §6.5 + §6.6) ──────────────


class LessonCreateRequest(BaseModel):
    """Admin payload for `POST /api/v1/admin/decks/{deck_id}/lessons` (§6.4).

    `deck_id` is read from the URL path; `version`, `version_type`,
    `published_at`, `quality_score`, `source_content_id`,
    `generated_by_model` are server-set.
    """

    slug: str = Field(..., min_length=1, max_length=100, pattern=_SLUG_PATTERN)
    title: str = Field(..., min_length=1, max_length=200)
    concept_md: str = Field(..., min_length=1)
    production_md: str = Field(..., min_length=1)
    examples_md: str = Field(..., min_length=1)
    display_order: int = Field(default=0, ge=0)


class LessonUpdateRequest(BaseModel):
    """Admin payload for `PATCH /api/v1/admin/lessons/{lesson_id}` (§6.5).

    `edit_classification` is required; admin's intent. BE re-validates
    against the §7 rule and raises 409 on disagreement.
    """

    edit_classification: EditClassification
    slug: Optional[str] = Field(
        default=None, min_length=1, max_length=100, pattern=_SLUG_PATTERN
    )
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    concept_md: Optional[str] = Field(default=None, min_length=1)
    production_md: Optional[str] = Field(default=None, min_length=1)
    examples_md: Optional[str] = Field(default=None, min_length=1)
    display_order: Optional[int] = Field(default=None, ge=0)


class LessonUpdateResponse(BaseModel):
    """Response shape for PATCH on lessons (§6.6).

    Extends `LessonResponse` additively with cascade-outcome fields so
    the FE can surface "N quiz_items were retired" on substantive edits.
    """

    lesson: LessonResponse
    version_type_applied: EditClassification
    quiz_items_retired_count: int
    quiz_items_retired_ids: list[str]

    model_config = ConfigDict(from_attributes=True)
