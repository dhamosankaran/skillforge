"""Pydantic v2 response schemas for the user-self FSRS dashboard.

Spec: docs/specs/phase-6/09-fsrs-dashboard.md §5 + §12 D-1..D-14.

Single-envelope response per D-3. The FE mirrors these field-for-field
in `src/types/index.ts` per curriculum.md §9.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── §5.2 cards-due ──────────────────────────────────────────────────────────


class CardsDueByState(BaseModel):
    """FSRS-state breakdown of `quiz_item_progress` rows."""

    new: int
    learning: int
    review: int
    relearning: int


class CardsDueSection(BaseModel):
    """Cards due today + next 7 days + per-state breakdown.

    `due_today` counts progress rows with `due_date <= now()` AND
    state ∈ {learning, review, relearning} (state='new' has no due).
    Visibility filter chain applied per slice 6.5 invariants.
    """

    due_today: int
    due_next_7_days: int
    due_breakdown_by_state: CardsDueByState
    total_quiz_items_in_progress: int


# ── §5.3 retention curve (D-5 + D-6) ────────────────────────────────────────


class DailyRetentionPoint(BaseModel):
    """One bucket on the daily-retention curve.

    `date` is user-local per §12 D-6. `recall_rate` is null when
    `sample_size == 0` (continuous series — every date in the window
    appears even if zero reviews on that date).
    """

    model_config = ConfigDict(strict=False)

    date: date
    sample_size: int
    recall_rate: Optional[float]


class RetentionSection(BaseModel):
    """Aggregated recall + lapse over the retention window.

    Per §12 D-5: `overall_recall_rate` = `rating IN (3, 4)` / total;
    `overall_lapse_rate` = `rating == 1` / total. Hard ratings (2)
    intentionally excluded from both surfaces.
    """

    sample_size: int
    overall_recall_rate: float
    overall_lapse_rate: float
    daily_retention: list[DailyRetentionPoint]


# ── §5.4 deck mastery (D-8 + D-10) ──────────────────────────────────────────


class DeckMastery(BaseModel):
    """Per-deck mastery rollup.

    `mastery_pct = quiz_items_mastered / total_quiz_items_visible`
    where `mastered` = `state == 'review' AND reps >= 3` per §12 D-8.
    Persona-invisible / archived / retired / premium-for-free decks
    are filtered upstream by `curriculum_visibility` helpers (D-10).
    """

    deck_id: str
    deck_slug: str
    deck_title: str
    total_quiz_items_visible: int
    quiz_items_with_progress: int
    quiz_items_mastered: int
    mastery_pct: float


class DeckMasterySection(BaseModel):
    """Decks sorted by `mastery_pct DESC, display_order ASC`."""

    decks: list[DeckMastery]


# ── §5.5 streak (Phase-2 reuse) ─────────────────────────────────────────────


class StreakSection(BaseModel):
    """Reuses `gamification_service.get_stats` field-for-field.

    Exposed on the dashboard to avoid a second FE fetch.
    """

    current_streak: int
    longest_streak: int
    last_active_date: Optional[date]
    freezes_available: int
    total_xp: int


# ── §5.6 review history (D-9) ───────────────────────────────────────────────


class RecentReview(BaseModel):
    """One row in the review-history feed.

    Row click navigates to `/learn/lesson/<lesson_id>` per §12 D-9
    sub-decision (no inline drawer in v1).
    """

    quiz_item_id: str
    lesson_id: str
    lesson_title: str
    deck_slug: str
    rating: int
    fsrs_state_after: str
    reviewed_at: datetime


class ReviewHistorySection(BaseModel):
    """Newest-first reviews capped at `MAX_RECENT_REVIEWS` per §12 D-9."""

    window_days: int
    total_in_window: int
    recent_reviews: list[RecentReview]


# ── §5.1 envelope ──────────────────────────────────────────────────────────


class DashboardResponse(BaseModel):
    """Single envelope returned by `GET /api/v1/learn/dashboard`.

    Spec §5.1 + §12 D-3.

    `is_cold_start` = (no `quiz_item_progress` rows) AND (no
    `quiz_review_events` in the retention window). Both must be zero.
    """

    user_id: str
    persona: Optional[str]
    plan: Optional[str]
    is_cold_start: bool
    retention_window_days: int
    generated_at: datetime

    cards_due: CardsDueSection
    retention: RetentionSection
    deck_mastery: DeckMasterySection
    streak: StreakSection
    review_history: ReviewHistorySection
