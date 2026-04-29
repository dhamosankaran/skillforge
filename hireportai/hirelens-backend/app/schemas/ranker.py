"""Pydantic schemas for the Lens-ranked deck/lesson ordering surface.

Spec: docs/specs/phase-6/07-deck-lesson-ranker.md §5 + §12 D-1..D-16.

The ranker shapes deck-only output in v1 (D-5). ``RankedLesson`` and
the ``RankedDecksResponse.lessons`` field are forward-compat affordances
for a hypothetical slice 6.6b lesson-cross-deck surface; v1 always
returns ``lessons=None``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.deck import DeckResponse
from app.schemas.lesson import LessonResponse


class ScoreBreakdown(BaseModel):
    """Diagnostic per-signal sub-scores for a ranked deck.

    Each value is in ``[0, 1]`` after the per-signal normalisation
    described in spec §4.2.
    """

    gap_match: float
    fsrs_due: float
    avg_quality: float
    display_order_rank: float


class RankedDeck(BaseModel):
    """A deck with its composite score and matched-gap diagnostics."""

    deck: DeckResponse
    score: float
    rank: int
    matched_gaps: list[str]
    score_breakdown: ScoreBreakdown

    model_config = ConfigDict(from_attributes=True)


class RankedLesson(BaseModel):
    """Forward-compat shape for a hypothetical slice 6.6b lesson surface.

    v1 never populates per §12 D-5.
    """

    lesson: LessonResponse
    deck_id: str
    deck_slug: str
    score: float
    rank: int
    matched_gaps: list[str]

    model_config = ConfigDict(from_attributes=True)


class RankedDecksResponse(BaseModel):
    """Top-level response for ``GET /api/v1/learn/ranked-decks``.

    ``cold_start=True`` indicates the user has no recent scan with
    ``analysis_payload IS NOT NULL`` in the lookback window; decks are
    ordered by ``display_order ASC`` only and ``recent_gap_count`` is 0.
    Per §12 D-15 the BE response carries no copy hint — the FE consumer
    (slice 6.7) picks the cold-start CTA.
    """

    user_id: str
    persona: Optional[str] = None
    cold_start: bool
    lookback_days: int
    recent_gap_count: int
    ranked_at: datetime
    decks: list[RankedDeck]
    # Always None in v1 per §12 D-5; reserved for slice 6.6b.
    lessons: Optional[list[RankedLesson]] = None
