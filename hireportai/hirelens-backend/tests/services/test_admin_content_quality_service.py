"""Service-layer tests for `admin_content_quality_service` (Phase 6
slice 6.11 — B-084).

Spec: docs/specs/phase-6/11-content-quality-retention.md §10.1 +
§11 AC-3..AC-15 / AC-18 + §12 D-1..D-16.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.analytics_event import LessonViewEvent, QuizReviewEvent
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.services import admin_content_quality_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ────────────────────────────────────────────────────────────


async def _seed_deck(
    db_session,
    *,
    title: str = "Quality Test Deck",
    archived: bool = False,
    persona_visibility: str = "both",
    tier: str = "foundation",
    display_order: int = 0,
) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"quality-deck-{uuid.uuid4().hex[:8]}",
        title=title,
        description="seeded for quality tests",
        display_order=display_order,
        persona_visibility=persona_visibility,
        tier=tier,
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_lesson(
    db_session,
    *,
    deck_id: str,
    archived: bool = False,
    title: str | None = None,
) -> Lesson:
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title=title or "Quality Test Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=datetime.now(timezone.utc),
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _seed_quiz_item(
    db_session,
    *,
    lesson_id: str,
    question: str = "What is X?",
    retired: bool = False,
) -> QuizItem:
    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        question=question,
        answer="A.",
        question_type="free_text",
        difficulty="medium",
        display_order=0,
        version=1,
        retired_at=datetime.now(timezone.utc) if retired else None,
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
    reviewed_at: datetime | None = None,
) -> QuizReviewEvent:
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
        reviewed_at=reviewed_at or datetime.now(timezone.utc),
    )
    db_session.add(ev)
    await db_session.flush()
    return ev


async def _seed_view(
    db_session, *, lesson_id: str, deck_id: str, viewed_at: datetime | None = None
) -> LessonViewEvent:
    ev = LessonViewEvent(
        id=str(uuid.uuid4()),
        user_id=None,
        lesson_id=lesson_id,
        deck_id=deck_id,
        version=1,
        viewed_at=viewed_at or datetime.now(timezone.utc),
    )
    db_session.add(ev)
    await db_session.flush()
    return ev


# ── 1. Cold start (AC-4) ────────────────────────────────────────────────────


async def test_aggregate_dashboard_cold_start_with_no_reviews(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    await _seed_quiz_item(db_session, lesson_id=lesson.id)

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30, include_archived=False
    )

    assert response.is_cold_start is True
    assert response.window_days == 30
    assert response.include_archived is False
    assert response.worst_lessons == []
    assert response.worst_quiz_items == []
    assert response.writebacks_applied == 0
    # Decks still appear in cold start (admins may have empty content).
    assert len(response.decks) >= 1


# ── 2. Happy path (AC-3) ────────────────────────────────────────────────────


async def test_aggregate_dashboard_happy_path_populates_all_sections(
    db_session,
):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    for rating in [3, 4, 3, 4, 3]:
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

    assert response.is_cold_start is False
    deck_row = next((d for d in response.decks if d.deck_id == deck.id), None)
    assert deck_row is not None
    assert deck_row.review_count_window == 5
    assert deck_row.lesson_count == 1
    assert deck_row.weighted_pass_rate == 1.0
    lesson_row = next(
        (lr for lr in response.worst_lessons if lr.lesson_id == lesson.id), None
    )
    assert lesson_row is not None
    assert lesson_row.review_count_window == 5
    assert lesson_row.pass_rate == 1.0
    assert lesson_row.low_volume is True
    qi_row = next(
        (qr for qr in response.worst_quiz_items if qr.quiz_item_id == qi.id), None
    )
    assert qi_row is not None
    assert qi_row.review_count_window == 5
    assert qi_row.pass_rate == 1.0


# ── 3. Writeback fires above threshold (AC-5) ───────────────────────────────


async def test_writeback_fires_when_review_count_meets_threshold(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    # 10 reviews — exactly meets MIN_REVIEW_THRESHOLD; 7 pass + 3 lapse.
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

    assert response.writebacks_applied == 1
    refreshed = (
        await db_session.execute(select(Lesson).where(Lesson.id == lesson.id))
    ).scalar_one()
    assert refreshed.quality_score is not None
    # Bayesian-smoothed: (7 + 0.5*10) / (10 + 10) = 12 / 20 = 0.60
    assert Decimal(refreshed.quality_score) == Decimal("0.60")


# ── 4. Writeback skipped below threshold (AC-6) ─────────────────────────────


async def test_writeback_skipped_when_review_count_below_threshold(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)
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

    assert response.writebacks_applied == 0
    refreshed = (
        await db_session.execute(select(Lesson).where(Lesson.id == lesson.id))
    ).scalar_one()
    assert refreshed.quality_score is None
    lesson_row = next(
        lr for lr in response.worst_lessons if lr.lesson_id == lesson.id
    )
    assert lesson_row.low_volume is True
    assert lesson_row.smoothed_quality_score is None


# ── 5. Idempotency: re-runs are no-ops (AC-7) ───────────────────────────────


async def test_writeback_is_idempotent_on_repeated_aggregation(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    for rating in [3] * 10:
        await _seed_review(
            db_session,
            quiz_item_id=qi.id,
            lesson_id=lesson.id,
            deck_id=deck.id,
            rating=rating,
        )

    first = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )
    second = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )

    assert first.writebacks_applied == 1
    assert second.writebacks_applied == 0


# ── 6. include_archived=False excludes archived (AC-8) ──────────────────────


async def test_include_archived_false_excludes_archived_decks_and_lessons(
    db_session,
):
    archived_deck = await _seed_deck(db_session, archived=True)
    archived_lesson = await _seed_lesson(
        db_session, deck_id=archived_deck.id, archived=True
    )
    qi = await _seed_quiz_item(db_session, lesson_id=archived_lesson.id)
    await _seed_review(
        db_session,
        quiz_item_id=qi.id,
        lesson_id=archived_lesson.id,
        deck_id=archived_deck.id,
        rating=3,
    )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30, include_archived=False
    )

    assert all(d.deck_id != archived_deck.id for d in response.decks)
    assert all(
        lr.lesson_id != archived_lesson.id for lr in response.worst_lessons
    )


# ── 7. include_archived=True surfaces them flagged (AC-9) ───────────────────


async def test_include_archived_true_surfaces_archived_with_flag(db_session):
    archived_deck = await _seed_deck(db_session, archived=True)
    archived_lesson = await _seed_lesson(
        db_session, deck_id=archived_deck.id, archived=True
    )
    qi = await _seed_quiz_item(db_session, lesson_id=archived_lesson.id)
    await _seed_review(
        db_session,
        quiz_item_id=qi.id,
        lesson_id=archived_lesson.id,
        deck_id=archived_deck.id,
        rating=3,
    )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30, include_archived=True
    )

    deck_row = next(d for d in response.decks if d.deck_id == archived_deck.id)
    assert deck_row.archived is True
    lesson_row = next(
        lr for lr in response.worst_lessons if lr.lesson_id == archived_lesson.id
    )
    assert lesson_row.archived is True


# ── 8. Bayesian smoothing math (AC-15) ──────────────────────────────────────


@pytest.mark.parametrize(
    "passes,total,expected",
    [
        # (3 + 5) / (5 + 10) = 0.5333…
        (3, 5, 8 / 15),
        # (60 + 5) / (100 + 10) = 0.5909…
        (60, 100, 65 / 110),
        # (5 + 5) / (10 + 10) = 0.5
        (5, 10, 0.5),
    ],
)
def test_bayesian_smoothing_formula(passes, total, expected):
    result = admin_content_quality_service._smooth(passes, total)
    assert abs(result - expected) < 1e-9


# ── 9. Worst lessons cap (AC-13) ────────────────────────────────────────────


async def test_worst_lessons_cap_honoured_at_25(db_session):
    deck = await _seed_deck(db_session)
    for _ in range(30):
        lesson = await _seed_lesson(db_session, deck_id=deck.id)
        qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)
        await _seed_review(
            db_session,
            quiz_item_id=qi.id,
            lesson_id=lesson.id,
            deck_id=deck.id,
            rating=1,
        )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )

    assert len(response.worst_lessons) == 25


# ── 10. Hard rating excluded from pass + lapse (AC-18) ──────────────────────


async def test_hard_rating_excluded_from_pass_and_lapse(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    # 4 Hard (rating=2) + 4 Good (3) + 2 Again (1) = 10 total reviews.
    for rating in [2, 2, 2, 2, 3, 3, 3, 3, 1, 1]:
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
        qr for qr in response.worst_quiz_items if qr.quiz_item_id == qi.id
    )
    # passes = 4 Good / 10 reviews = 0.4
    assert qi_row.pass_rate == 0.4
    # lapses = 2 Again / 10 reviews = 0.2 (Hard NOT counted as lapse)
    assert qi_row.lapse_rate == 0.2


# ── 11. Sort order: lessons ASC NULLS LAST (AC-11) ──────────────────────────


async def test_worst_lessons_sorted_ascending_nulls_last(db_session):
    deck = await _seed_deck(db_session)
    # Lesson with low pass + high volume (smoothed score ~0.18)
    poor = await _seed_lesson(
        db_session, deck_id=deck.id, title="Poor lesson"
    )
    poor_qi = await _seed_quiz_item(db_session, lesson_id=poor.id)
    for _ in range(15):
        await _seed_review(
            db_session,
            quiz_item_id=poor_qi.id,
            lesson_id=poor.id,
            deck_id=deck.id,
            rating=1,
        )
    # Lesson with high pass + high volume (smoothed score ~0.83)
    good = await _seed_lesson(
        db_session, deck_id=deck.id, title="Good lesson"
    )
    good_qi = await _seed_quiz_item(db_session, lesson_id=good.id)
    for _ in range(15):
        await _seed_review(
            db_session,
            quiz_item_id=good_qi.id,
            lesson_id=good.id,
            deck_id=deck.id,
            rating=3,
        )
    # Low-volume lesson (smoothed=None) — should tail.
    low = await _seed_lesson(
        db_session, deck_id=deck.id, title="Low volume lesson"
    )
    low_qi = await _seed_quiz_item(db_session, lesson_id=low.id)
    for _ in range(2):
        await _seed_review(
            db_session,
            quiz_item_id=low_qi.id,
            lesson_id=low.id,
            deck_id=deck.id,
            rating=1,
        )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )
    target_ids = {poor.id, good.id, low.id}
    filtered = [
        lr for lr in response.worst_lessons if lr.lesson_id in target_ids
    ]
    # Order: poor (lowest smoothed) → good (highest smoothed) → low (None tail)
    assert filtered[0].lesson_id == poor.id
    assert filtered[1].lesson_id == good.id
    assert filtered[2].lesson_id == low.id
    assert filtered[2].smoothed_quality_score is None


# ── 12. View count flows from lesson_view_events (D-14) ─────────────────────


async def test_lesson_row_includes_view_count_from_lesson_view_events(
    db_session,
):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    await _seed_review(
        db_session,
        quiz_item_id=qi.id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=3,
    )
    for _ in range(7):
        await _seed_view(db_session, lesson_id=lesson.id, deck_id=deck.id)

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )
    lesson_row = next(
        lr for lr in response.worst_lessons if lr.lesson_id == lesson.id
    )
    assert lesson_row.view_count_window == 7


# ── 13. Window clamp respected — old reviews excluded (D-3) ─────────────────


async def test_window_excludes_reviews_older_than_window(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    # Inside window (10 days ago).
    inside = datetime.now(timezone.utc) - timedelta(days=10)
    await _seed_review(
        db_session,
        quiz_item_id=qi.id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=3,
        reviewed_at=inside,
    )
    # Outside window (60 days ago).
    outside = datetime.now(timezone.utc) - timedelta(days=60)
    await _seed_review(
        db_session,
        quiz_item_id=qi.id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=1,
        reviewed_at=outside,
    )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )
    lesson_row = next(
        lr for lr in response.worst_lessons if lr.lesson_id == lesson.id
    )
    # Only the inside-window review counted: 1 review, 1 pass.
    assert lesson_row.review_count_window == 1
    assert lesson_row.pass_rate == 1.0


# ── 14. Retired quiz_items excluded (D-8) ───────────────────────────────────


async def test_retired_quiz_items_are_excluded_from_worst_quiz_items(
    db_session,
):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    retired_qi = await _seed_quiz_item(
        db_session, lesson_id=lesson.id, retired=True
    )
    await _seed_review(
        db_session,
        quiz_item_id=retired_qi.id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=1,
    )

    response = await admin_content_quality_service.aggregate_dashboard(
        db_session, window_days=30
    )

    assert all(
        qr.quiz_item_id != retired_qi.id for qr in response.worst_quiz_items
    )
