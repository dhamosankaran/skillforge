"""Admin content-quality dashboard schemas — Phase 6 slice 6.11.

Spec: docs/specs/phase-6/11-content-quality-retention.md §5 +
§12 D-1..D-16.

Single-envelope response per D-6 mirroring slice 6.8 `DashboardResponse`
shape — one fetch renders the whole admin observability page (per-deck
rollup + worst-lessons + worst-quiz_items). FE mirrors these
field-for-field in `src/types/index.ts`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class DeckQualityRow(BaseModel):
    """Per-deck rollup (§5.2).

    `weighted_pass_rate` is the review-count-weighted mean of per-lesson
    pass_rates. `avg_quality_score` is the simple mean of non-NULL
    `lessons.quality_score` values within the deck (excludes lessons
    that haven't yet crossed the writeback threshold per D-4).
    """

    deck_id: str
    deck_slug: str
    deck_title: str
    tier: Literal["foundation", "premium"]
    persona_visibility: Literal["climber", "interview_prepper", "both"]
    archived: bool
    lesson_count: int
    review_count_window: int
    weighted_pass_rate: Optional[float]
    avg_quality_score: Optional[float]


class LessonQualityRow(BaseModel):
    """Per-lesson worst-first row (§5.3).

    `pass_rate` is the raw fraction `count(rating in (3,4)) / total`.
    `smoothed_quality_score` applies the §6.1 Bayesian smoothing prior
    only when `review_count_window >= MIN_REVIEW_THRESHOLD` (D-4);
    below threshold it stays None and `low_volume` is True.
    `persisted_quality_score` echoes the post-writeback
    `lessons.quality_score` value on disk (so the dashboard surfaces
    what the ranker actually consumes).
    """

    lesson_id: str
    lesson_slug: str
    lesson_title: str
    deck_id: str
    deck_slug: str
    review_count_window: int
    view_count_window: int
    pass_rate: Optional[float]
    smoothed_quality_score: Optional[float]
    persisted_quality_score: Optional[float]
    low_volume: bool
    archived: bool
    published_at: Optional[datetime]
    # Slice 6.13.5a additions per §5.3 — populated from card_quality_signals.
    # `critique_scores` keys ⊆ {'accuracy','clarity','completeness','cohesion'}.
    # `thumbs_aggregate` + `thumbs_count` always None / 0 in 6.13.5a (no
    # thumbs route yet); 6.13.5b populates them via the same field shape.
    critique_scores: Optional[dict[str, float]] = None
    thumbs_aggregate: Optional[float] = None
    thumbs_count: int = 0


class QuizItemQualityRow(BaseModel):
    """Per-quiz_item worst-first row (§5.4).

    Read-time aggregation only — per-quiz_item writeback to disk is
    out-of-scope per §12 D-5 / D-9 (deferred to slice 6.13.5
    `card_quality_signals`). `lapse_rate` is `count(rating == 1) /
    total`; rating=2 (Hard) is excluded from both pass and lapse
    counts per slice 6.8 D-5 (mirrored at §12 D-13).
    `question_preview` is the first 80 chars of the quiz_item question
    (visual scan only).
    """

    quiz_item_id: str
    lesson_id: str
    deck_id: str
    question_preview: str
    review_count_window: int
    pass_rate: Optional[float]
    lapse_rate: Optional[float]
    low_volume: bool
    retired: bool
    # Slice 6.13.5a additions per §5.3 — per-quiz_item user-aggregate
    # writeback now persists when ``review_count_window >=
    # MIN_REVIEW_THRESHOLD`` so the dashboard surfaces what was
    # actually written to ``card_quality_signals``. ``thumbs_aggregate``
    # + ``thumbs_count`` always None / 0 in 6.13.5a (no thumbs route yet).
    pass_rate_persisted: Optional[float] = None
    thumbs_aggregate: Optional[float] = None
    thumbs_count: int = 0


class AdminContentQualityResponse(BaseModel):
    """Single-envelope admin content-quality dashboard response (§5.1).

    Mirrors slice 6.8 `DashboardResponse` envelope shape. All section
    arrays are present on every response — cold-start sends empty lists
    rather than omitting keys, so the FE renders cold-start variants
    without conditional-key handling.
    """

    window_days: int
    include_archived: bool
    generated_at: datetime
    is_cold_start: bool
    decks: list[DeckQualityRow]
    worst_lessons: list[LessonQualityRow]
    worst_quiz_items: list[QuizItemQualityRow]
    writebacks_applied: int
