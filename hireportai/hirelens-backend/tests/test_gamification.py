"""Unit tests for app/services/gamification_service.py.

Coverage:
  - test_xp_awarded_correctly        — single award updates total_xp
  - test_streak_increments_on_daily_activity
                                     — first activity sets streak=1, next-day
                                       award bumps to 2, longest_streak follows
  - test_streak_resets_on_missed_day — gap of 2+ days zeroes the streak
  - test_badge_earned_at_threshold   — crossing xp_100 awards the badge once

Tests bypass the route layer and call the service directly using the
``db_session`` fixture from conftest.py. The badge catalog is seeded inside
each test because the test schema is built via ``Base.metadata.create_all``
rather than alembic migrations (so the migration's bulk_insert never runs).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.models.gamification import Badge, GamificationStats, UserBadge
from app.models.user import User
from app.services import gamification_service as gs

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _make_user(db) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@gam-test.com",
        name="Gamification Tester",
    )
    db.add(user)
    await db.flush()
    return user


async def _seed_badges(db) -> None:
    """Mirror the alembic seed for the in-test create_all schema."""
    for b in gs.BADGES:
        existing = await db.get(Badge, b.id)
        if existing is not None:
            continue
        db.add(
            Badge(
                id=b.id,
                name=b.name,
                description=b.name,
                threshold_type=b.threshold_type,
                threshold_value=b.threshold_value,
            )
        )
    await db.flush()


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_xp_awarded_correctly(db_session):
    """A single review award credits exactly 10 XP and creates the stats row."""
    await _seed_badges(db_session)
    user = await _make_user(db_session)

    stats, _ = await gs.award_xp(user.id, 10, "review", db_session)

    assert stats.total_xp == 10
    # The same row should be reachable via direct lookup.
    fetched = await db_session.get(GamificationStats, user.id)
    assert fetched is not None
    assert fetched.total_xp == 10


async def test_streak_increments_on_daily_activity(db_session, monkeypatch):
    """Streak goes 1 → 2 across consecutive UTC days; longest tracks max."""
    await _seed_badges(db_session)
    user = await _make_user(db_session)

    day1 = date(2026, 4, 1)
    day2 = date(2026, 4, 2)

    monkeypatch.setattr(gs, "_today_utc", lambda: day1)
    stats, _ = await gs.award_xp(user.id, 10, "review", db_session)
    assert stats.current_streak == 1
    assert stats.longest_streak == 1
    assert stats.last_active_date == day1

    monkeypatch.setattr(gs, "_today_utc", lambda: day2)
    stats, _ = await gs.award_xp(user.id, 10, "review", db_session)
    assert stats.current_streak == 2
    assert stats.longest_streak == 2
    assert stats.last_active_date == day2

    # A second award on the same day must NOT double-count the streak.
    stats, _ = await gs.award_xp(user.id, 10, "review", db_session)
    assert stats.current_streak == 2
    assert stats.total_xp == 30


async def test_streak_resets_on_missed_day(db_session, monkeypatch):
    """A 2-day gap zeroes current_streak but preserves longest_streak."""
    await _seed_badges(db_session)
    user = await _make_user(db_session)

    day1 = date(2026, 4, 1)
    day2 = date(2026, 4, 2)
    day_after_gap = date(2026, 4, 5)  # missed day3 and day4

    monkeypatch.setattr(gs, "_today_utc", lambda: day1)
    await gs.award_xp(user.id, 10, "review", db_session)
    monkeypatch.setattr(gs, "_today_utc", lambda: day2)
    await gs.award_xp(user.id, 10, "review", db_session)

    # Lazy reset on read after the gap.
    monkeypatch.setattr(gs, "_today_utc", lambda: day_after_gap)
    view = await gs.get_stats(user.id, db_session)
    assert view.current_streak == 0
    assert view.longest_streak == 2  # historical max preserved

    # New activity on day_after_gap restarts the streak at 1.
    stats, _ = await gs.award_xp(user.id, 10, "review", db_session)
    assert stats.current_streak == 1
    assert stats.longest_streak == 2


async def test_badge_earned_at_threshold(db_session, monkeypatch):
    """Crossing 100 XP awards xp_100 exactly once."""
    await _seed_badges(db_session)
    user = await _make_user(db_session)

    # Pin the date so streak side-effects don't change behavior across days.
    monkeypatch.setattr(gs, "_today_utc", lambda: date(2026, 4, 1))

    newly_earned: list[str] = []
    for _ in range(10):  # 10 × 10 XP = 100 → crosses xp_100 threshold
        _, n = await gs.award_xp(user.id, 10, "review", db_session)
        newly_earned.extend(n)

    assert "xp_100" in newly_earned
    # first_review event-badge should also fire on the first review.
    assert "first_review" in newly_earned

    # Idempotency: re-evaluating after another award must not duplicate xp_100.
    pre_count = len(
        (
            await db_session.execute(
                UserBadge.__table__.select().where(UserBadge.user_id == user.id)
            )
        ).all()
    )
    _, n2 = await gs.award_xp(user.id, 10, "review", db_session)
    assert "xp_100" not in n2
    post_count = len(
        (
            await db_session.execute(
                UserBadge.__table__.select().where(UserBadge.user_id == user.id)
            )
        ).all()
    )
    assert pre_count == post_count
