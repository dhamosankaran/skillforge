"""Tests for app/services/progress_service.py.

Coverage:
  - test_radar_returns_all_categories  — every seeded category appears in the
    radar response with correct mastery_pct (AC-1)
  - test_heatmap_shows_activity_days   — heatmap returns the requested number
    of days, reviewed day has correct count (AC-2)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.user import User
from app.services import progress_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _make_user(db) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@progress-test.com",
        name="Progress Tester",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_category(db, name: str) -> Category:
    cat = Category(
        id=str(uuid.uuid4()),
        name=name,
        icon="📚",
        color="from-blue-500 to-cyan-500",
        display_order=0,
        source="foundation",
    )
    db.add(cat)
    await db.flush()
    return cat


async def _make_card(db, category_id: str) -> Card:
    card = Card(
        id=str(uuid.uuid4()),
        category_id=category_id,
        question="Q?",
        answer="A.",
        difficulty="easy",
        tags=[],
    )
    db.add(card)
    await db.flush()
    return card


async def _make_progress(
    db,
    user_id: str,
    card_id: str,
    state: str = "review",
    last_reviewed: datetime | None = None,
) -> CardProgress:
    cp = CardProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        card_id=card_id,
        state=state,
        stability=1.0,
        difficulty_fsrs=5.0,
        elapsed_days=1.0,
        scheduled_days=1.0,
        reps=1,
        lapses=0,
        last_reviewed=last_reviewed or datetime.now(timezone.utc),
    )
    db.add(cp)
    await db.flush()
    return cp


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_radar_returns_all_categories(db_session):
    """Every seeded category appears in the radar with correct mastery_pct.

    Setup: 2 categories. Cat-A has 2 cards (1 mastered, 1 learning).
    Cat-B has 1 card (unstudied). Expected:
      Cat-A: mastery_pct = 50.0  (1 review / 2 total)
      Cat-B: mastery_pct = 0.0   (0 review / 1 total)
    """
    user = await _make_user(db_session)

    cat_a = await _make_category(db_session, f"Radar-A-{uuid.uuid4().hex[:6]}")
    cat_b = await _make_category(db_session, f"Radar-B-{uuid.uuid4().hex[:6]}")

    card_a1 = await _make_card(db_session, cat_a.id)
    card_a2 = await _make_card(db_session, cat_a.id)
    await _make_card(db_session, cat_b.id)  # unstudied card

    await _make_progress(db_session, user.id, card_a1.id, state="review")
    await _make_progress(db_session, user.id, card_a2.id, state="learning")

    result = await progress_service.get_category_coverage(user.id, db_session)

    by_name = {r.category: r for r in result}

    assert cat_a.name in by_name
    assert cat_b.name in by_name

    ra = by_name[cat_a.name]
    assert ra.total_cards == 2
    assert ra.studied == 2
    assert ra.mastery_pct == 50.0

    rb = by_name[cat_b.name]
    assert rb.total_cards == 1
    assert rb.studied == 0
    assert rb.mastery_pct == 0.0


async def test_heatmap_shows_activity_days(db_session):
    """Heatmap returns `days` entries; reviewed day has correct count.

    Setup: 1 card reviewed today. Request 7-day heatmap.
    Expected: 7 entries, today's entry has review_count >= 1, other days = 0.
    """
    user = await _make_user(db_session)
    cat = await _make_category(db_session, f"Heatmap-{uuid.uuid4().hex[:6]}")
    card = await _make_card(db_session, cat.id)

    now = datetime.now(timezone.utc)
    await _make_progress(db_session, user.id, card.id, state="learning", last_reviewed=now)

    result = await progress_service.get_activity_heatmap(user.id, 7, db_session)

    assert len(result) == 7

    # Most recent (index 0) should be today
    today = date.today()
    assert result[0].date == today
    assert result[0].review_count >= 1

    # A day in the past with no reviews should be 0
    past_entries = [d for d in result if d.date != today]
    for entry in past_entries:
        assert entry.review_count == 0
