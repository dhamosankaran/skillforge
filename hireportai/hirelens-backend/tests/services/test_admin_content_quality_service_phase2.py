"""Tests for slice 6.13.5a extensions to ``admin_content_quality_service``.

Spec: docs/specs/phase-6/12-quality-signals.md §6.5 + §11 AC-11..AC-14.

Covers the additions slice 6.13.5a layered on top of slice 6.11's
single-envelope dashboard:

- Per-quiz_item user-aggregate writeback to ``card_quality_signals``
  (AC-11 / AC-12).
- ``LessonQualityRow.critique_scores`` populated when critique signals
  exist (AC-13).
- ``QuizItemQualityRow.pass_rate_persisted`` populated post-writeback.
- 6.13.5b-deferred fields (``thumbs_aggregate`` / ``thumbs_count``)
  always None / 0 in this slice.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.analytics_event import LessonViewEvent, QuizReviewEvent
from app.models.card_quality_signal import CardQualitySignal
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.schemas.card_quality_signal import CardQualitySignalWrite
from app.services import (
    admin_content_quality_service,
    card_quality_signal_service,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ────────────────────────────────────────────────────────────


async def _seed_deck(db_session, *, archived: bool = False) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"p2-deck-{uuid.uuid4().hex[:8]}",
        title="P2 Deck",
        description="seed",
        display_order=0,
        persona_visibility="both",
        tier="foundation",
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_lesson(db_session, deck_id: str) -> Lesson:
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"p2-lesson-{uuid.uuid4().hex[:6]}",
        title="P2 Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _seed_quiz_item(db_session, lesson_id: str) -> QuizItem:
    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        question="Q?",
        answer="A.",
        question_type="free_text",
        difficulty="medium",
        display_order=0,
        version=1,
    )
    db_session.add(qi)
    await db_session.flush()
    return qi


async def _seed_review(
    db_session,
    *,
    quiz_item_id: str,
    lesson_id: str,
    deck_id: str,
    rating: int,
):
    ev = QuizReviewEvent(
        id=str(uuid.uuid4()),
        user_id=None,
        quiz_item_id=quiz_item_id,
        lesson_id=lesson_id,
        deck_id=deck_id,
        rating=rating,
        fsrs_state_before="learning",
        fsrs_state_after="review",
        reps=1,
        lapses=0,
        time_spent_ms=1000,
        reviewed_at=datetime.now(timezone.utc),
    )
    db_session.add(ev)
    await db_session.flush()


# ── 1. AC-11: per-quiz_item writeback above threshold ──────────────────────


async def test_quiz_item_user_review_writeback_persists_above_threshold(
    db_session,
):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)
    # 10 reviews — 7 pass + 3 lapse (smoothed = (7 + 5) / 20 = 0.6).
    for rating in [3, 3, 3, 3, 3, 3, 3, 1, 1, 1]:
        await _seed_review(
            db_session,
            quiz_item_id=qi.id,
            lesson_id=lesson.id,
            deck_id=deck.id,
            rating=rating,
        )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )

    qi_row = next(
        r for r in response.worst_quiz_items if r.quiz_item_id == qi.id
    )
    assert qi_row.pass_rate_persisted == 0.6

    # Underlying card_quality_signals row exists with the expected shape.
    persisted = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.quiz_item_id == qi.id,
                CardQualitySignal.signal_source == "user_review",
            )
        )
    ).scalars().all()
    assert len(persisted) == 1
    assert float(persisted[0].score) == 0.6
    assert persisted[0].dimension == "pass_rate"
    assert persisted[0].recorded_by_user_id is None
    assert persisted[0].lesson_id == lesson.id


# ── 2. AC-12: per-quiz_item writeback skipped below threshold ──────────────


async def test_quiz_item_writeback_skipped_below_threshold(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)
    for rating in [3, 3, 1]:  # 3 reviews — below MIN_REVIEW_THRESHOLD
        await _seed_review(
            db_session,
            quiz_item_id=qi.id,
            lesson_id=lesson.id,
            deck_id=deck.id,
            rating=rating,
        )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )

    qi_row = next(
        r for r in response.worst_quiz_items if r.quiz_item_id == qi.id
    )
    assert qi_row.pass_rate_persisted is None

    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.quiz_item_id == qi.id,
            )
        )
    ).scalars().all()
    assert rows == []


# ── 3. AC-13: critique_scores populated when signals exist ─────────────────


async def test_lesson_row_surfaces_critique_scores_when_present(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)
    # Need at least one review so the lesson appears in worst_lessons.
    await _seed_review(
        db_session,
        quiz_item_id=qi.id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=3,
    )

    # Pre-seed two critique-signal rows.
    for dim, score in [("accuracy", 0.8), ("clarity", 0.6)]:
        await card_quality_signal_service.upsert_signal(
            CardQualitySignalWrite(
                lesson_id=lesson.id,
                signal_source="critique",
                dimension=dim,
                score=score,
                source_ref="job-pre",
            ),
            db_session,
        )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )

    lesson_row = next(
        r for r in response.worst_lessons if r.lesson_id == lesson.id
    )
    assert lesson_row.critique_scores is not None
    assert lesson_row.critique_scores["accuracy"] == 0.8
    assert lesson_row.critique_scores["clarity"] == 0.6


# ── 4. critique_scores absent → None ───────────────────────────────────────


async def test_lesson_row_critique_scores_none_when_cold(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)
    await _seed_review(
        db_session,
        quiz_item_id=qi.id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=3,
    )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )

    lesson_row = next(
        r for r in response.worst_lessons if r.lesson_id == lesson.id
    )
    assert lesson_row.critique_scores is None


# ── 5. 6.13.5b-deferred thumbs fields default empty ────────────────────────


async def test_thumbs_fields_default_to_empty_in_613_5a(db_session):
    """`thumbs_aggregate` / `thumbs_count` default to None / 0 until 6.13.5b."""
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)
    await _seed_review(
        db_session,
        quiz_item_id=qi.id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=3,
    )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )

    lesson_row = next(
        r for r in response.worst_lessons if r.lesson_id == lesson.id
    )
    qi_row = next(
        r for r in response.worst_quiz_items if r.quiz_item_id == qi.id
    )
    assert lesson_row.thumbs_aggregate is None
    assert lesson_row.thumbs_count == 0
    assert qi_row.thumbs_aggregate is None
    assert qi_row.thumbs_count == 0


# ── 6. AC-19: FK CASCADE on lesson_id ──────────────────────────────────────


async def test_signal_row_cascades_on_lesson_delete(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            signal_source="critique",
            dimension="accuracy",
            score=0.8,
        ),
        db_session,
    )

    await db_session.delete(lesson)
    await db_session.flush()

    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.lesson_id == lesson.id
            )
        )
    ).scalars().all()
    assert rows == []
