"""Unit tests for app/services/mission_service.py.

Coverage:
  - test_create_mission_calculates_daily_target
  - test_daily_cards_from_mission_categories
  - test_countdown_decrements
  - test_mission_complete

Tests bypass the route layer and call the service directly using the
``db_session`` fixture from conftest.py.
"""
from __future__ import annotations

import math
import uuid
from datetime import date, timedelta

import pytest

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.user import User
from app.services import mission_service as ms

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _make_user(db) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@mission-test.com",
        name="Mission Tester",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_category(db, name: str = "System Design") -> Category:
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"{name}-{uuid.uuid4().hex[:6]}",
        icon="📐",
        color="blue",
        display_order=0,
    )
    db.add(cat)
    await db.flush()
    return cat


async def _make_cards(db, category: Category, count: int = 10) -> list[Card]:
    cards = []
    for i in range(count):
        card = Card(
            id=str(uuid.uuid4()),
            category_id=category.id,
            question=f"Q{i + 1}: What is concept {i + 1}?",
            answer=f"A{i + 1}: Explanation of concept {i + 1}.",
            difficulty="medium",
            tags=["test"],
        )
        db.add(card)
        cards.append(card)
    await db.flush()
    return cards


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_mission_calculates_daily_target(db_session, monkeypatch):
    """Creating a 7-day mission with 14 cards → daily_target = ceil(14/7) = 2."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, "Algorithms")
    await _make_cards(db_session, cat, count=14)

    today = date(2026, 4, 10)
    target = date(2026, 4, 16)  # 7 days inclusive
    monkeypatch.setattr(ms, "_today_utc", lambda: today)

    mission = await ms.create_mission(
        user_id=user.id,
        title="Algo Sprint",
        target_date=target,
        category_ids=[cat.id],
        db=db_session,
    )

    days_remaining = (target - today).days + 1  # 7
    expected_target = math.ceil(14 / days_remaining)  # 2

    assert mission.daily_target == expected_target
    assert mission.status == "active"
    assert len(mission.days) == days_remaining
    assert mission.days[0].day_number == 1
    assert mission.days[-1].day_number == days_remaining
    assert all(d.cards_target == expected_target for d in mission.days)


async def test_daily_cards_from_mission_categories(db_session, monkeypatch):
    """Daily pull returns only cards from the mission's selected categories."""
    user = await _make_user(db_session)
    cat_selected = await _make_category(db_session, "RAG")
    cat_other = await _make_category(db_session, "Networking")
    selected_cards = await _make_cards(db_session, cat_selected, count=5)
    await _make_cards(db_session, cat_other, count=5)

    today = date(2026, 4, 10)
    target = date(2026, 4, 14)  # 5 days
    monkeypatch.setattr(ms, "_today_utc", lambda: today)

    mission = await ms.create_mission(
        user_id=user.id,
        title="RAG Deep Dive",
        target_date=target,
        category_ids=[cat_selected.id],
        db=db_session,
    )

    _, today_day, cards = await ms.get_mission_daily_cards(
        user_id=user.id, db=db_session
    )

    # Should only contain cards from the selected category
    selected_ids = {c.id for c in selected_cards}
    returned_ids = {c["id"] for c in cards}
    assert returned_ids.issubset(selected_ids)
    assert len(cards) > 0
    assert len(cards) <= today_day.cards_target


async def test_countdown_decrements(db_session, monkeypatch):
    """Days remaining decreases as time passes."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, "Databases")
    await _make_cards(db_session, cat, count=10)

    day1 = date(2026, 4, 10)
    target = date(2026, 4, 14)  # 5 days
    monkeypatch.setattr(ms, "_today_utc", lambda: day1)

    await ms.create_mission(
        user_id=user.id,
        title="DB Sprint",
        target_date=target,
        category_ids=[cat.id],
        db=db_session,
    )

    # Day 1: 5 days remaining
    mission = await ms.get_active_mission(user_id=user.id, db=db_session)
    days_remaining_d1 = (mission.target_date - day1).days + 1
    assert days_remaining_d1 == 5

    # Day 3: 3 days remaining
    day3 = date(2026, 4, 12)
    monkeypatch.setattr(ms, "_today_utc", lambda: day3)
    mission = await ms.get_active_mission(user_id=user.id, db=db_session)
    days_remaining_d3 = (mission.target_date - day3).days + 1
    assert days_remaining_d3 == 3

    # Countdown actually decremented
    assert days_remaining_d3 < days_remaining_d1


async def test_mission_complete(db_session, monkeypatch):
    """Mission status transitions to 'completed' when all day targets are met."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, "Concurrency")
    await _make_cards(db_session, cat, count=4)

    today = date(2026, 4, 10)
    target = date(2026, 4, 11)  # 2 days, ceil(4/2) = 2 cards/day
    monkeypatch.setattr(ms, "_today_utc", lambda: today)

    mission = await ms.create_mission(
        user_id=user.id,
        title="Quick Sprint",
        target_date=target,
        category_ids=[cat.id],
        db=db_session,
    )

    assert mission.status == "active"
    assert mission.daily_target == 2

    # Complete day 1
    returned_mission, day, xp = await ms.complete_mission_day(
        user_id=user.id, db=db_session
    )
    assert day.cards_completed == day.cards_target
    assert xp == 50  # daily_complete XP

    # Move to day 2 and complete
    day2 = date(2026, 4, 11)
    monkeypatch.setattr(ms, "_today_utc", lambda: day2)

    returned_mission, day2_obj, xp2 = await ms.complete_mission_day(
        user_id=user.id, db=db_session
    )

    # 2 days × 2 cards/day = 4 total completed == 4 total cards → completed
    assert returned_mission.status == "completed"
    assert xp2 == 50
