"""Unit tests for app/services/study_service.py.

Tests call the service layer directly (no HTTP) using the shared db_session
fixture.  The test database starts empty (schema only), and each test's session
is rolled back on teardown, so tests are fully isolated.

Test coverage:
  TC-01  Good rating on a Review card increases the interval (scheduled_days > 1)
  TC-02  Again rating on a Review card transitions to Relearning + near-future due
  TC-03  First-ever review creates a card_progress row
  TC-04  Daily queue returns at most 5 cards when 10 are due
  TC-05  Daily queue returns empty when no overdue/unreviewed cards exist
  TC-06  Free-plan gate: only foundation-category cards appear in queue
  TC-07  Easy rating produces a longer interval than Good from identical state
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.user import User
from app.services import study_service

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ── Seed helpers ──────────────────────────────────────────────────────────────


async def _make_user(db) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@study-test.com",
        name="Study Tester",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_category(db, source: str = "foundation") -> Category:
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"Cat-{uuid.uuid4().hex[:6]}",
        icon="📚",
        color="from-blue-500 to-indigo-600",
        display_order=99,
        source=source,
    )
    db.add(cat)
    await db.flush()
    return cat


async def _make_card(db, category_id: str) -> Card:
    card = Card(
        id=str(uuid.uuid4()),
        category_id=category_id,
        question=f"Q-{uuid.uuid4().hex[:6]}?",
        answer="Answer.",
        difficulty="medium",
        tags=[],
    )
    db.add(card)
    await db.flush()
    return card


async def _make_progress(
    db,
    user_id: str,
    card_id: str,
    *,
    state: str = "review",
    stability: float = 10.0,
    difficulty_fsrs: float = 5.0,
    reps: int = 3,
    lapses: int = 0,
    due_delta_hours: float = -1.0,  # negative = past due
    fsrs_step: int | None = None,
) -> CardProgress:
    """Insert a CardProgress row with configurable scheduling state."""
    now = datetime.now(timezone.utc)
    cp = CardProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        card_id=card_id,
        state=state,
        stability=stability,
        difficulty_fsrs=difficulty_fsrs,
        elapsed_days=0.0,
        scheduled_days=10.0,
        reps=reps,
        lapses=lapses,
        fsrs_step=fsrs_step,
        due_date=now + timedelta(hours=due_delta_hours),
        last_reviewed=now - timedelta(days=10),
    )
    db.add(cp)
    await db.flush()
    return cp


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_good_rating_increases_interval(db_session):
    """TC-01: Good (3) on a Review card must schedule the next review ≥ 1 day out."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    card = await _make_card(db_session, cat.id)
    await _make_progress(db_session, user.id, card.id, state="review", reps=3)

    result = await study_service.review_card(
        user_id=user.id,
        card_id=card.id,
        rating=3,  # Good
        is_free=False,
        db=db_session,
    )

    assert result.fsrs_state == "review", f"expected 'review', got {result.fsrs_state!r}"
    assert result.scheduled_days >= 1.0, (
        f"Good on Review card should schedule ≥ 1 day ahead; got {result.scheduled_days:.3f}"
    )
    assert result.reps == 4, f"reps should be 4 (was 3, incremented by Good); got {result.reps}"
    assert result.lapses == 0


async def test_again_rating_resets_to_today(db_session):
    """TC-02: Again (1) on a Review card transitions to Relearning with near-future due."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    card = await _make_card(db_session, cat.id)
    await _make_progress(
        db_session, user.id, card.id, state="review", stability=10.0, reps=5
    )

    result = await study_service.review_card(
        user_id=user.id,
        card_id=card.id,
        rating=1,  # Again
        is_free=False,
        db=db_session,
    )

    assert result.fsrs_state == "relearning", (
        f"Again on Review should transition to 'relearning'; got {result.fsrs_state!r}"
    )
    assert result.lapses == 1, f"lapses should be 1; got {result.lapses}"
    # Due date must be within 15 minutes of now
    now = datetime.now(timezone.utc)
    minutes_until_due = (result.due_date - now).total_seconds() / 60
    assert 0 <= minutes_until_due <= 15, (
        f"After Again, due_date should be within 15 min; got {minutes_until_due:.1f} min"
    )


async def test_first_review_creates_progress_row(db_session):
    """TC-03: Reviewing a card for the first time creates a card_progress row."""
    from sqlalchemy import select as sa_select

    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    card = await _make_card(db_session, cat.id)

    # No card_progress row exists yet
    existing = (
        await db_session.execute(
            sa_select(CardProgress)
            .where(CardProgress.user_id == user.id)
            .where(CardProgress.card_id == card.id)
        )
    ).scalar_one_or_none()
    assert existing is None, "Expected no progress row before first review"

    result = await study_service.review_card(
        user_id=user.id,
        card_id=card.id,
        rating=3,  # Good
        is_free=False,
        db=db_session,
    )

    # Row should now exist
    created = (
        await db_session.execute(
            sa_select(CardProgress)
            .where(CardProgress.user_id == user.id)
            .where(CardProgress.card_id == card.id)
        )
    ).scalar_one_or_none()
    assert created is not None, "card_progress row must be created on first review"
    assert created.state != "new", f"state should not remain 'new'; got {created.state!r}"
    assert result.reps == 1, f"reps should be 1 after first Good review; got {result.reps}"


async def test_daily_five_returns_max_five(db_session):
    """TC-04: Daily queue is capped at 5 even when 10 cards are overdue."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)

    # Create 10 cards, all overdue
    for _ in range(10):
        card = await _make_card(db_session, cat.id)
        await _make_progress(
            db_session, user.id, card.id, state="review", due_delta_hours=-24.0
        )

    result = await study_service.get_daily_review(
        user_id=user.id,
        is_free=False,
        db=db_session,
    )

    assert len(result.cards) == 5, (
        f"Daily queue must return at most 5 cards; got {len(result.cards)}"
    )
    assert result.total_due == 5


async def test_daily_returns_empty_when_nothing_due(db_session):
    """TC-05: Queue is empty when all accessible cards have a future due_date."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, source="foundation")

    # Create 3 cards, all reviewed with due_date = tomorrow
    for _ in range(3):
        card = await _make_card(db_session, cat.id)
        await _make_progress(
            db_session, user.id, card.id, state="review", due_delta_hours=+24.0
        )

    # Free-plan user: only sees foundation (which are all future-due above)
    result = await study_service.get_daily_review(
        user_id=user.id,
        is_free=True,
        db=db_session,
    )

    assert len(result.cards) == 0, (
        f"Queue should be empty when all cards are future-due; got {len(result.cards)} cards"
    )
    assert result.total_due == 0


async def test_free_user_sees_only_foundation_cards(db_session):
    """TC-06: Free-plan users only receive cards from source='foundation' categories."""
    user = await _make_user(db_session)
    foundation_cat = await _make_category(db_session, source="foundation")
    premium_cat = await _make_category(db_session, source="premium")

    # 2 overdue foundation cards
    foundation_card_ids = set()
    for _ in range(2):
        card = await _make_card(db_session, foundation_cat.id)
        await _make_progress(
            db_session, user.id, card.id, state="review", due_delta_hours=-24.0
        )
        foundation_card_ids.add(card.id)

    # 3 overdue premium cards
    premium_card_ids = set()
    for _ in range(3):
        card = await _make_card(db_session, premium_cat.id)
        await _make_progress(
            db_session, user.id, card.id, state="review", due_delta_hours=-24.0
        )
        premium_card_ids.add(card.id)

    result = await study_service.get_daily_review(
        user_id=user.id,
        is_free=True,  # ← free-plan gate active
        db=db_session,
    )

    returned_ids = {item.card_id for item in result.cards}
    assert returned_ids <= foundation_card_ids, (
        f"Free user received non-foundation cards: {returned_ids - foundation_card_ids}"
    )
    assert len(result.cards) == 2, (
        f"Expected 2 foundation cards due; got {len(result.cards)}"
    )


async def test_easy_rating_longer_interval_than_good(db_session):
    """TC-07: Easy (4) on a Review card schedules a longer interval than Good (3)."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)

    # Two cards with identical starting state
    card_good = await _make_card(db_session, cat.id)
    card_easy = await _make_card(db_session, cat.id)
    await _make_progress(
        db_session, user.id, card_good.id, state="review", stability=5.0, reps=3
    )
    await _make_progress(
        db_session, user.id, card_easy.id, state="review", stability=5.0, reps=3
    )

    result_good = await study_service.review_card(
        user_id=user.id, card_id=card_good.id, rating=3, is_free=False, db=db_session
    )
    result_easy = await study_service.review_card(
        user_id=user.id, card_id=card_easy.id, rating=4, is_free=False, db=db_session
    )

    assert result_easy.scheduled_days > result_good.scheduled_days, (
        f"Easy interval ({result_easy.scheduled_days:.2f}d) should exceed "
        f"Good interval ({result_good.scheduled_days:.2f}d)"
    )


async def test_review_card_not_found_raises(db_session):
    """TC-10: Reviewing a non-existent card_id raises CardNotFoundError."""
    user = await _make_user(db_session)

    with pytest.raises(study_service.CardNotFoundError):
        await study_service.review_card(
            user_id=user.id,
            card_id=str(uuid.uuid4()),  # bogus UUID
            rating=3,
            is_free=False,
            db=db_session,
        )


async def test_review_free_user_premium_card_raises(db_session):
    """TC-09: Free user reviewing a premium-category card raises CardForbiddenError."""
    user = await _make_user(db_session)
    premium_cat = await _make_category(db_session, source="premium")
    card = await _make_card(db_session, premium_cat.id)

    with pytest.raises(study_service.CardForbiddenError):
        await study_service.review_card(
            user_id=user.id,
            card_id=card.id,
            rating=3,
            is_free=True,  # ← free-plan gate
            db=db_session,
        )


# ── Gamification wiring ──────────────────────────────────────────────────────
# These tests verify that study_service.review_card credits XP and ticks the
# streak via the gamification service. The wiring is critical because the rest
# of the gamification UX (badges, daily 5 bonus) hangs off these XP awards.


async def test_review_card_awards_xp(db_session):
    """Each successful review credits exactly 10 XP via gamification_service."""
    from app.services import gamification_service

    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    card = await _make_card(db_session, cat.id)
    await _make_progress(db_session, user.id, card.id, state="review")

    await study_service.review_card(
        user_id=user.id,
        card_id=card.id,
        rating=3,
        is_free=False,
        db=db_session,
    )

    stats = await gamification_service.get_stats(user.id, db_session)
    assert stats.total_xp == 10
    # Streak should also have ticked to 1 on the first activity of the day.
    assert stats.current_streak == 1


async def test_daily_five_completion_awards_bonus(db_session):
    """Reviewing the 5th unique card today triggers a 50 XP daily bonus.

    Total XP after 5 reviews should be 5×10 (per-review) + 50 (daily bonus) =
    100. A 6th review on the same day must NOT re-fire the bonus, so the
    total only grows by 10 more.
    """
    from app.services import gamification_service

    user = await _make_user(db_session)
    cat = await _make_category(db_session)

    cards = [await _make_card(db_session, cat.id) for _ in range(6)]
    for c in cards[:5]:
        await _make_progress(db_session, user.id, c.id, state="review")
        await study_service.review_card(
            user_id=user.id,
            card_id=c.id,
            rating=3,
            is_free=False,
            db=db_session,
        )

    stats = await gamification_service.get_stats(user.id, db_session)
    assert stats.total_xp == 5 * 10 + 50, (
        f"expected 100 XP (5 reviews + daily bonus), got {stats.total_xp}"
    )

    # 6th unique review on the same day → +10 only, no second bonus.
    await _make_progress(db_session, user.id, cards[5].id, state="review")
    await study_service.review_card(
        user_id=user.id,
        card_id=cards[5].id,
        rating=3,
        is_free=False,
        db=db_session,
    )
    stats = await gamification_service.get_stats(user.id, db_session)
    assert stats.total_xp == 110, (
        f"6th review must not refire the daily bonus; got {stats.total_xp}"
    )


# ── B-019 — DailyReviewResponse.completed_today ───────────────────────────


async def test_completed_today_false_before_any_reviews(db_session):
    """B-019: fresh user with overdue + fresh-fill sees completed_today=False."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    for _ in range(3):
        card = await _make_card(db_session, cat.id)
        await _make_progress(
            db_session, user.id, card.id, state="review", due_delta_hours=-24.0
        )

    result = await study_service.get_daily_review(
        user_id=user.id, is_free=False, db=db_session,
    )
    assert result.total_due == 3
    assert result.completed_today is False


async def test_completed_today_true_after_reviewing_five(db_session):
    """B-019 core bug: after 5 distinct reviews today (UTC), completed_today
    is True even when fresh-fill keeps total_due > 0."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    # 5 cards the user will review today (marked as already reviewed today).
    now = datetime.now(timezone.utc)
    for _ in range(5):
        card = await _make_card(db_session, cat.id)
        cp = await _make_progress(
            db_session, user.id, card.id, state="review",
            due_delta_hours=+24.0,  # pushed to tomorrow by FSRS
        )
        cp.last_reviewed = now  # simulate "reviewed today"
        db_session.add(cp)
    # Plus 10 fresh unseen cards — pass-2 will refill the queue from these.
    for _ in range(10):
        await _make_card(db_session, cat.id)
    await db_session.flush()

    result = await study_service.get_daily_review(
        user_id=user.id, is_free=False, db=db_session,
    )
    # Core regression evidence: queue still returns cards (fresh-fill) but
    # the flag is true so the widget can flip to done-state anyway.
    assert result.total_due == 5, (
        "fresh-fill still fills the queue — that's the bug the flag sidesteps"
    )
    assert result.completed_today is True


async def test_completed_today_small_library_reachable(db_session):
    """B-019: a user whose foundation library is smaller than _DAILY_GOAL can
    still reach completed_today=True by exhausting the pool."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, source="foundation")
    # Library is 3 cards; user already reviewed all 3 today.
    now = datetime.now(timezone.utc)
    for _ in range(3):
        card = await _make_card(db_session, cat.id)
        cp = await _make_progress(
            db_session, user.id, card.id, state="review",
            due_delta_hours=+24.0,
        )
        cp.last_reviewed = now
        db_session.add(cp)
    await db_session.flush()

    result = await study_service.get_daily_review(
        user_id=user.id, is_free=True, db=db_session,
    )
    assert result.total_due == 0, "all 3 cards are future-due and none unseen"
    assert result.completed_today is True, (
        "small-library users must reach a done state — threshold clamps to pool size"
    )


async def test_completed_today_partial_progress_still_false(db_session):
    """B-019: user has reviewed some (< goal) today, queue has more left;
    completed_today must remain False."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    now = datetime.now(timezone.utc)
    # 2 cards already reviewed today.
    for _ in range(2):
        card = await _make_card(db_session, cat.id)
        cp = await _make_progress(
            db_session, user.id, card.id, state="review",
            due_delta_hours=+24.0,
        )
        cp.last_reviewed = now
        db_session.add(cp)
    # 3 overdue + 10 unseen so pool is clearly >= _DAILY_GOAL.
    for _ in range(3):
        card = await _make_card(db_session, cat.id)
        await _make_progress(
            db_session, user.id, card.id, state="review", due_delta_hours=-24.0
        )
    for _ in range(10):
        await _make_card(db_session, cat.id)
    await db_session.flush()

    result = await study_service.get_daily_review(
        user_id=user.id, is_free=False, db=db_session,
    )
    assert result.total_due == 5
    assert result.completed_today is False


async def test_completed_today_ignores_reviews_before_today_start(db_session):
    """B-019: reviews from yesterday do not count toward today's threshold.
    Threshold uses today-start UTC, matching the daily_complete XP bonus."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    # 5 cards reviewed yesterday — must not count.
    yesterday = datetime.now(timezone.utc) - timedelta(days=2)
    for _ in range(5):
        card = await _make_card(db_session, cat.id)
        cp = await _make_progress(
            db_session, user.id, card.id, state="review",
            due_delta_hours=-24.0,
        )
        cp.last_reviewed = yesterday
        db_session.add(cp)
    await db_session.flush()

    result = await study_service.get_daily_review(
        user_id=user.id, is_free=False, db=db_session,
    )
    # Queue re-includes them as overdue.
    assert result.total_due == 5
    assert result.completed_today is False, (
        "yesterday's reviews are not today's reviews"
    )
