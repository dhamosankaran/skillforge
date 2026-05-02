"""Pydantic schemas for ``card_quality_signals`` (Phase 6 slice 6.13.5a + 6.13.5b).

Spec: docs/specs/phase-6/12-quality-signals.md §5.2 + §5.4.

Internal schemas (``CardQualitySignalWrite`` / ``CardQualitySignalRow``)
shipped in 6.13.5a; HTTP-boundary thumbs schemas (``ThumbsRequest`` /
``ThumbsResponse``) appended by 6.13.5b alongside the user-thumbs route.

``CardQualitySignalWrite`` is service-internal: callers
(``critique_signal_consumer``, ``admin_content_quality_service``,
``thumbs_service``) construct it; we never accept it directly at the
HTTP boundary. Per-source dimension / score validation is handled at
the service layer rather than the schema so the same write shape
covers all three signal sources.

``CardQualitySignalRow`` is the read shape for admin-side aggregations.

``ThumbsRequest`` / ``ThumbsResponse`` are the user-thumbs HTTP shapes
mounted at ``POST /api/v1/lessons/:lesson_id/thumbs`` (§12 D-7
lesson-level only v1).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SignalSource = Literal["critique", "user_review", "user_thumbs"]


class CardQualitySignalWrite(BaseModel):
    """Service-internal write payload for ``card_quality_signal_service``.

    Score is normalised before reaching here (critique 1..5 → divide by
    5.0; user_review smoothed pass_rate ∈ [0, 1]; user_thumbs ∈ {-1, +1}).
    The DB column is ``Numeric(4, 2)`` so score is bounded but the schema
    keeps a generous range to allow future dimensions on a 0..10 grade
    without a follow-up migration.
    """

    lesson_id: str
    quiz_item_id: Optional[str] = None
    signal_source: SignalSource
    dimension: str = Field(..., min_length=1, max_length=30)
    score: float = Field(..., ge=-1.0, le=10.0)
    source_ref: Optional[str] = None
    recorded_by_user_id: Optional[str] = None


class CardQualitySignalRow(BaseModel):
    """Read row for admin-side rollups + service-side aggregations."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    lesson_id: str
    quiz_item_id: Optional[str] = None
    signal_source: SignalSource
    dimension: str
    score: float
    source_ref: Optional[str] = None
    recorded_by_user_id: Optional[str] = None
    recorded_at: datetime


# ── Slice 6.13.5b — user-thumbs HTTP-boundary shapes (§5.4) ──────────────────


class ThumbsRequest(BaseModel):
    """User-side thumbs route input.

    Lesson-level only v1 per §12 D-7. Score is constrained to {-1, +1}
    via ``Literal``; FastAPI returns 422 on any other value (AC-8).
    Sticky thumbs v1 per §12 D-11 — POST with score=0 is rejected at
    the schema boundary (no clear-thumbs path).
    """

    score: Literal[-1, 1]


class ThumbsResponse(BaseModel):
    """User-side thumbs route output + initial-state read shape (§12 D-12).

    Returned by ``POST /api/v1/lessons/:id/thumbs`` and embedded as
    ``LessonWithQuizzesResponse.viewer_thumbs`` so the FE seeds
    ``<ThumbsControl />`` initial state from the lesson detail GET
    without a second round-trip.
    """

    accepted: bool
    score: Literal[-1, 1]
    aggregate_score: Optional[float] = None
    aggregate_count: int = 0
