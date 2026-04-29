"""Service-layer tests for `dashboard_service` (Phase 6 slice 6.8).

Spec: docs/specs/phase-6/09-fsrs-dashboard.md §10.1 + §11 AC-1..AC-13
+ §12 D-1..D-14.

Mirrors the seed-helpers pattern from `test_deck_ranker_service.py`
(slice 6.6).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.models.analytics_event import QuizReviewEvent
from app.models.deck import Deck
from app.models.email_preference import EmailPreference
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.quiz_item_progress import QuizItemProgress
from app.models.subscription import Subscription
from app.models.user import User
from app.services import dashboard_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ─────────────────────────────────────────────────────────────


async def _seed_user(
    db_session,
    *,
    persona: str | None = "interview_prepper",
    plan: str = "free",
) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@dashboard-svc-test.com",
        name="Dashboard Svc Tester",
        persona=persona,
    )
    db_session.add(user)
    await db_session.flush()
    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        plan=plan,
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()
    await db_session.refresh(user, attribute_names=["subscription"])
    return user


async def _seed_deck(
    db_session,
    *,
    slug: str | None = None,
    title: str = "Generic Deck",
    persona_visibility: str = "both",
    tier: str = "foundation",
    archived: bool = False,
    display_order: int = 0,
) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=slug or f"deck-{uuid.uuid4().hex[:8]}",
        title=title,
        description="seeded for dashboard tests",
        display_order=display_order,
        persona_visibility=persona_visibility,
        tier=tier,
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_lesson(
    db_session, *, deck_id: str, published: bool = True
) -> Lesson:
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Dashboard Svc Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=datetime.now(timezone.utc) if published else None,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _seed_quiz_item(
    db_session, *, lesson_id: str, retired: bool = False
) -> QuizItem:
    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        question="Q?",
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


async def _seed_progress(
    db_session,
    *,
    user_id: str,
    quiz_item_id: str,
    state: str = "review",
    due_at: datetime | None = None,
    reps: int = 0,
) -> QuizItemProgress:
    progress = QuizItemProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        quiz_item_id=quiz_item_id,
        state=state,
        due_date=due_at or datetime.now(timezone.utc),
        reps=reps,
    )
    db_session.add(progress)
    await db_session.flush()
    return progress


async def _seed_review_event(
    db_session,
    *,
    user_id: str,
    quiz_item_id: str,
    lesson_id: str,
    deck_id: str,
    rating: int = 3,
    reviewed_at: datetime | None = None,
) -> QuizReviewEvent:
    ev = QuizReviewEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
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


# ── 1. Cold start (AC-2 + G-5) ───────────────────────────────────────────────


async def test_aggregate_user_dashboard_cold_start_for_fresh_user(db_session):
    user = await _seed_user(db_session)
    response = await dashboard_service.aggregate_user_dashboard(user, db_session)

    assert response.is_cold_start is True
    assert response.cards_due.total_quiz_items_in_progress == 0
    assert response.cards_due.due_today == 0
    assert response.retention.sample_size == 0
    assert response.retention.overall_recall_rate == 0.0
    assert response.review_history.total_in_window == 0
    assert response.review_history.recent_reviews == []
    # Continuous series: every date in the window appears even with 0 reviews.
    assert len(response.retention.daily_retention) == 30
    assert all(p.sample_size == 0 for p in response.retention.daily_retention)
    assert all(p.recall_rate is None for p in response.retention.daily_retention)


# ── 2. Cards-due happy path (AC-3) ───────────────────────────────────────────


async def test_aggregate_user_dashboard_cards_due_counts_visible_progress(
    db_session,
):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi_due = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    qi_future = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    qi_new = await _seed_quiz_item(db_session, lesson_id=lesson.id)

    now = datetime.now(timezone.utc)
    await _seed_progress(
        db_session,
        user_id=user.id,
        quiz_item_id=qi_due.id,
        state="review",
        due_at=now - timedelta(hours=1),
        reps=2,
    )
    await _seed_progress(
        db_session,
        user_id=user.id,
        quiz_item_id=qi_future.id,
        state="review",
        due_at=now + timedelta(days=10),
        reps=1,
    )
    await _seed_progress(
        db_session,
        user_id=user.id,
        quiz_item_id=qi_new.id,
        state="new",
    )

    response = await dashboard_service.aggregate_user_dashboard(user, db_session)

    assert response.is_cold_start is False
    assert response.cards_due.due_today == 1
    assert response.cards_due.due_next_7_days == 1
    assert response.cards_due.total_quiz_items_in_progress == 3
    assert response.cards_due.due_breakdown_by_state.review == 2
    assert response.cards_due.due_breakdown_by_state.new == 1


# ── 3. Retention curve continuous series (AC-6) ─────────────────────────────


async def test_aggregate_user_dashboard_retention_curve_fills_zero_days(
    db_session,
):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)

    # Only one event 5 days ago — every other window day has sample=0.
    await _seed_review_event(
        db_session,
        user_id=user.id,
        quiz_item_id=qi.id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=3,  # Good — counts as recall per D-5
        reviewed_at=datetime.now(timezone.utc) - timedelta(days=5),
    )

    response = await dashboard_service.aggregate_user_dashboard(
        user, db_session, retention_window_days=7
    )

    assert response.retention.sample_size == 1
    assert response.retention.overall_recall_rate == 1.0
    assert response.retention.overall_lapse_rate == 0.0
    assert len(response.retention.daily_retention) == 7
    sampled_days = [p for p in response.retention.daily_retention if p.sample_size > 0]
    zero_days = [p for p in response.retention.daily_retention if p.sample_size == 0]
    assert len(sampled_days) == 1
    assert sampled_days[0].recall_rate == 1.0
    assert len(zero_days) == 6
    assert all(p.recall_rate is None for p in zero_days)


# ── 4. D-5 recall = (3,4); Hard=2 not counted as recall ─────────────────────


async def test_aggregate_user_dashboard_recall_excludes_hard_ratings(
    db_session,
):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)

    base = datetime.now(timezone.utc) - timedelta(days=1)
    # 1 Again (lapse), 1 Hard (neither), 1 Good (recall), 1 Easy (recall)
    for rating in (1, 2, 3, 4):
        await _seed_review_event(
            db_session,
            user_id=user.id,
            quiz_item_id=qi.id,
            lesson_id=lesson.id,
            deck_id=deck.id,
            rating=rating,
            reviewed_at=base,
        )

    response = await dashboard_service.aggregate_user_dashboard(user, db_session)

    assert response.retention.sample_size == 4
    assert response.retention.overall_recall_rate == 0.5  # 2/4 — Hard excluded
    assert response.retention.overall_lapse_rate == 0.25  # 1/4


# ── 5. Deck mastery filters retired/archived/persona-invisible (AC-4 + AC-6) ─


async def test_aggregate_user_dashboard_deck_mastery_filters_invisible_decks(
    db_session,
):
    user = await _seed_user(db_session, persona="interview_prepper")
    visible = await _seed_deck(db_session, slug="visible", title="Visible")
    archived = await _seed_deck(
        db_session, slug="arch", title="Archived", archived=True
    )
    other_persona = await _seed_deck(
        db_session,
        slug="climber-only",
        title="Climber Only",
        persona_visibility="career_climber",
    )

    response = await dashboard_service.aggregate_user_dashboard(user, db_session)

    deck_ids = {d.deck_id for d in response.deck_mastery.decks}
    assert visible.id in deck_ids
    assert archived.id not in deck_ids
    assert other_persona.id not in deck_ids


# ── 6. Deck mastery hides premium decks for free users (AC-5 + D-10) ────────


async def test_aggregate_user_dashboard_deck_mastery_hides_premium_for_free(
    db_session,
):
    free_user = await _seed_user(db_session, plan="free")
    foundation = await _seed_deck(db_session, slug="found", tier="foundation")
    premium = await _seed_deck(db_session, slug="prem", tier="premium")

    response = await dashboard_service.aggregate_user_dashboard(
        free_user, db_session
    )

    deck_ids = {d.deck_id for d in response.deck_mastery.decks}
    assert foundation.id in deck_ids
    assert premium.id not in deck_ids


# ── 7. Mastery threshold per D-8 (state == review AND reps >= 3) ────────────


async def test_aggregate_user_dashboard_mastery_threshold_reps_three(db_session):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session, slug="mastery-deck")
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi_mastered = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    qi_almost = await _seed_quiz_item(db_session, lesson_id=lesson.id)
    qi_learning = await _seed_quiz_item(db_session, lesson_id=lesson.id)

    await _seed_progress(
        db_session,
        user_id=user.id,
        quiz_item_id=qi_mastered.id,
        state="review",
        reps=3,
    )
    await _seed_progress(
        db_session,
        user_id=user.id,
        quiz_item_id=qi_almost.id,
        state="review",
        reps=2,  # below threshold
    )
    await _seed_progress(
        db_session,
        user_id=user.id,
        quiz_item_id=qi_learning.id,
        state="learning",
        reps=5,  # wrong state
    )

    response = await dashboard_service.aggregate_user_dashboard(user, db_session)
    deck_row = next(d for d in response.deck_mastery.decks if d.deck_id == deck.id)

    assert deck_row.total_quiz_items_visible == 3
    assert deck_row.quiz_items_with_progress == 3
    assert deck_row.quiz_items_mastered == 1
    assert deck_row.mastery_pct == pytest.approx(1 / 3)


# ── 8. Streak section reuses gamification_service (AC-7 + §6.3) ─────────────


async def test_aggregate_user_dashboard_streak_section_reuses_gamification(
    db_session,
):
    user = await _seed_user(db_session)
    response = await dashboard_service.aggregate_user_dashboard(user, db_session)

    # Fresh user → gamification auto-creates a stats row at zero
    assert response.streak.current_streak == 0
    assert response.streak.longest_streak == 0
    assert response.streak.total_xp == 0


# ── 9. Review-history newest-first cap + JOIN to lesson/deck (D-9) ──────────


async def test_aggregate_user_dashboard_review_history_newest_first_capped(
    db_session,
):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session, slug="rh-deck")
    lesson = await _seed_lesson(db_session, deck_id=deck.id)
    qi = await _seed_quiz_item(db_session, lesson_id=lesson.id)

    base = datetime.now(timezone.utc) - timedelta(days=2)
    # 25 events; cap should clamp to MAX_RECENT_REVIEWS (20)
    for i in range(25):
        await _seed_review_event(
            db_session,
            user_id=user.id,
            quiz_item_id=qi.id,
            lesson_id=lesson.id,
            deck_id=deck.id,
            rating=3,
            reviewed_at=base + timedelta(seconds=i),
        )

    response = await dashboard_service.aggregate_user_dashboard(user, db_session)

    assert response.review_history.total_in_window == 25
    assert len(response.review_history.recent_reviews) == 20
    timestamps = [r.reviewed_at for r in response.review_history.recent_reviews]
    assert timestamps == sorted(timestamps, reverse=True)
    first = response.review_history.recent_reviews[0]
    assert first.deck_slug == "rh-deck"
    assert first.lesson_title == lesson.title


# ── 10. User timezone read from email_preferences (D-6) ─────────────────────


async def test_aggregate_user_dashboard_user_local_date_bucketing(db_session):
    user = await _seed_user(db_session)
    pref = EmailPreference(
        user_id=user.id,
        timezone="America/Los_Angeles",
    )
    db_session.add(pref)
    await db_session.flush()

    response = await dashboard_service.aggregate_user_dashboard(user, db_session)
    # Daily-retention dates use LA timezone — compare to current LA date.
    from zoneinfo import ZoneInfo

    expected_today = datetime.now(timezone.utc).astimezone(
        ZoneInfo("America/Los_Angeles")
    ).date()
    assert response.retention.daily_retention[-1].date == expected_today
