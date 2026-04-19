"""Mission Mode service — time-bound study sprints with FSRS-prioritised cards.

Public API:
  - create_mission(user_id, title, target_date, category_ids, db)
  - get_active_mission(user_id, db)
  - get_mission_daily_cards(user_id, db)
  - complete_mission_day(user_id, db)
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.mission import Mission, MissionDay, mission_categories
from app.services import gamification_service, home_state_service


# ── Errors ──────────────────────────────────────────────────────────────────


class MissionNotFoundError(Exception):
    pass


class MissionConflictError(Exception):
    """User already has an active mission."""
    pass


class MissionInvalidError(ValueError):
    pass


class MissionGoneError(Exception):
    """Mission is completed or abandoned."""
    pass


# ── Helpers ─────────────────────────────────────────────────────────────────


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


async def _count_cards_for_categories(
    category_ids: list[str], db: AsyncSession
) -> int:
    """Count total cards across the given categories."""
    result = await db.execute(
        select(sa_func.count(Card.id)).where(Card.category_id.in_(category_ids))
    )
    return result.scalar_one()


async def _rebalance(mission: Mission, today: date, db: AsyncSession) -> None:
    """Redistribute remaining cards across future mission days.

    Called when the user opens their mission and there are past days with
    incomplete cards. Also updates the mission's daily_target field.
    """
    category_ids = [c.id for c in mission.categories]
    total_cards = await _count_cards_for_categories(category_ids, db)

    # Sum completed cards across all past days (before today)
    past_completed = 0
    future_days: list[MissionDay] = []
    today_day: MissionDay | None = None

    for day in mission.days:
        if day.date < today:
            past_completed += day.cards_completed
        elif day.date == today:
            today_day = day
            past_completed += day.cards_completed
            future_days.append(day)
        else:
            future_days.append(day)

    remaining_cards = max(0, total_cards - past_completed)
    remaining_day_count = len(future_days)

    if remaining_day_count == 0:
        return

    # For today's day, don't count already-completed cards in the target
    if today_day is not None:
        # Today still counts as a remaining day, but we need to account for
        # cards already done today
        cards_left_today_and_future = remaining_cards
        new_daily_target = max(1, math.ceil(cards_left_today_and_future / remaining_day_count))
    else:
        new_daily_target = max(1, math.ceil(remaining_cards / remaining_day_count))

    for day in future_days:
        day.cards_target = new_daily_target

    mission.daily_target = new_daily_target
    await db.flush()


# ── Public API ──────────────────────────────────────────────────────────────


async def create_mission(
    user_id: str,
    title: str,
    target_date: date,
    category_ids: list[str],
    db: AsyncSession,
) -> Mission:
    """Create a new mission for the user.

    Validates:
      - target_date is not in the past
      - category_ids are not empty and contain cards
      - user has no other active mission
    """
    today = _today_utc()

    if target_date < today:
        raise MissionInvalidError("target_date cannot be in the past")

    if not category_ids:
        raise MissionInvalidError("At least one category is required")

    # Check for existing active mission
    existing = (
        await db.execute(
            select(Mission)
            .where(Mission.user_id == user_id)
            .where(Mission.status == "active")
        )
    ).scalar_one_or_none()

    if existing is not None:
        raise MissionConflictError("User already has an active mission")

    # Validate categories exist and have cards
    categories = (
        await db.execute(
            select(Category).where(Category.id.in_(category_ids))
        )
    ).scalars().all()

    if len(categories) != len(category_ids):
        raise MissionInvalidError("One or more category IDs are invalid")

    total_cards = await _count_cards_for_categories(category_ids, db)
    if total_cards == 0:
        raise MissionInvalidError("Selected categories have no cards")

    # Calculate daily target
    days_remaining = (target_date - today).days + 1  # inclusive
    daily_target = math.ceil(total_cards / days_remaining)

    # Create mission
    mission = Mission(
        user_id=user_id,
        title=title,
        target_date=target_date,
        daily_target=daily_target,
        status="active",
    )
    db.add(mission)
    await db.flush()

    # Link categories via association table
    for cat_id in category_ids:
        await db.execute(
            mission_categories.insert().values(
                mission_id=mission.id, category_id=cat_id
            )
        )

    # Pre-generate mission_days
    for i in range(days_remaining):
        day_date = today + timedelta(days=i)
        day = MissionDay(
            mission_id=mission.id,
            day_number=i + 1,
            date=day_date,
            cards_target=daily_target,
            cards_completed=0,
        )
        db.add(day)

    await db.flush()

    # Reload relationships
    await db.refresh(mission, ["categories", "days"])

    analytics_track(
        user_id=user_id,
        event="mission_created",
        properties={
            "days": days_remaining,
            "categories": category_ids,
            "total_cards": total_cards,
            "daily_target": daily_target,
        },
    )

    home_state_service.invalidate(user_id)

    return mission


async def get_active_mission(user_id: str, db: AsyncSession) -> Mission:
    """Return the user's current active mission with countdown info.

    Raises MissionNotFoundError if no active mission exists.
    """
    mission = (
        await db.execute(
            select(Mission)
            .where(Mission.user_id == user_id)
            .where(Mission.status == "active")
        )
    ).scalar_one_or_none()

    if mission is None:
        raise MissionNotFoundError("No active mission found")

    today = _today_utc()

    # Auto-complete if target_date has passed
    if mission.target_date < today:
        mission.status = "completed"
        await db.flush()

        category_ids = [c.id for c in mission.categories]
        total_cards = await _count_cards_for_categories(category_ids, db)
        total_completed = sum(d.cards_completed for d in mission.days)
        coverage = (total_completed / total_cards * 100) if total_cards > 0 else 0

        analytics_track(
            user_id=user_id,
            event="mission_completed",
            properties={
                "total_days": len(mission.days),
                "coverage_pct": round(coverage, 1),
            },
        )

    return mission


async def get_mission_daily_cards(
    user_id: str, db: AsyncSession
) -> tuple[Mission, MissionDay, list[dict]]:
    """Return today's FSRS-prioritised card set for the user's active mission.

    Triggers rebalancing if past days have incomplete cards.

    Returns (mission, today_day, cards_list).
    Raises MissionNotFoundError, MissionGoneError.
    """
    mission = (
        await db.execute(
            select(Mission)
            .where(Mission.user_id == user_id)
            .where(Mission.status == "active")
        )
    ).scalar_one_or_none()

    if mission is None:
        raise MissionNotFoundError("No active mission found")

    if mission.status in ("completed", "abandoned"):
        raise MissionGoneError("Mission is no longer active")

    today = _today_utc()
    now = datetime.now(timezone.utc)

    # Find today's mission_day
    today_day: MissionDay | None = None
    has_deficit = False
    for day in mission.days:
        if day.date == today:
            today_day = day
        elif day.date < today and day.cards_completed < day.cards_target:
            has_deficit = True

    if today_day is None:
        raise MissionGoneError("No mission day for today — mission may have ended")

    # Rebalance if there's a deficit from missed days
    if has_deficit:
        await _rebalance(mission, today, db)
        await db.refresh(today_day)

    # How many cards still needed today
    cards_needed = max(0, today_day.cards_target - today_day.cards_completed)

    if cards_needed == 0:
        return mission, today_day, []

    category_ids = [c.id for c in mission.categories]

    # FSRS-prioritised card pull:
    # 1. Overdue cards (due_date <= now)
    # 2. New cards (no progress row)
    # 3. Soonest-due among remaining

    # Pass 1: overdue cards with progress
    overdue_stmt = (
        select(Card, Category)
        .join(Category, Category.id == Card.category_id)
        .join(CardProgress, CardProgress.card_id == Card.id)
        .where(Card.category_id.in_(category_ids))
        .where(CardProgress.user_id == user_id)
        .where(CardProgress.due_date <= now)
        .order_by(CardProgress.due_date.asc())
        .limit(cards_needed)
    )
    overdue_rows = (await db.execute(overdue_stmt)).all()

    cards: list[dict] = []
    seen_ids: set[str] = set()
    for row in overdue_rows:
        card, cat = row.Card, row.Category
        cards.append({
            "id": card.id,
            "question": card.question,
            "answer": card.answer,
            "category": cat.name,
            "difficulty": card.difficulty,
        })
        seen_ids.add(card.id)

    remaining = cards_needed - len(cards)

    # Pass 2: new cards (no progress row for this user)
    if remaining > 0:
        reviewed_ids_sq = (
            select(CardProgress.card_id)
            .where(CardProgress.user_id == user_id)
            .scalar_subquery()
        )
        new_stmt = (
            select(Card, Category)
            .join(Category, Category.id == Card.category_id)
            .where(Card.category_id.in_(category_ids))
            .where(Card.id.not_in(reviewed_ids_sq))
            .order_by(Card.created_at.asc())
            .limit(remaining)
        )
        new_rows = (await db.execute(new_stmt)).all()
        for row in new_rows:
            card, cat = row.Card, row.Category
            if card.id not in seen_ids:
                cards.append({
                    "id": card.id,
                    "question": card.question,
                    "answer": card.answer,
                    "category": cat.name,
                    "difficulty": card.difficulty,
                })
                seen_ids.add(card.id)

    remaining = cards_needed - len(cards)

    # Pass 3: soonest-due cards (already reviewed but not yet overdue)
    if remaining > 0:
        upcoming_stmt = (
            select(Card, Category)
            .join(Category, Category.id == Card.category_id)
            .join(CardProgress, CardProgress.card_id == Card.id)
            .where(Card.category_id.in_(category_ids))
            .where(CardProgress.user_id == user_id)
            .where(CardProgress.due_date > now)
            .where(Card.id.not_in(list(seen_ids)) if seen_ids else True)
            .order_by(CardProgress.due_date.asc())
            .limit(remaining)
        )
        upcoming_rows = (await db.execute(upcoming_stmt)).all()
        for row in upcoming_rows:
            card, cat = row.Card, row.Category
            if card.id not in seen_ids:
                cards.append({
                    "id": card.id,
                    "question": card.question,
                    "answer": card.answer,
                    "category": cat.name,
                    "difficulty": card.difficulty,
                })
                seen_ids.add(card.id)

    return mission, today_day, cards


async def complete_mission_day(
    user_id: str, db: AsyncSession
) -> tuple[Mission, MissionDay, int]:
    """Mark today's mission day as complete and award XP.

    Returns (mission, today_day, xp_awarded).
    """
    mission = (
        await db.execute(
            select(Mission)
            .where(Mission.user_id == user_id)
            .where(Mission.status == "active")
        )
    ).scalar_one_or_none()

    if mission is None:
        raise MissionNotFoundError("No active mission found")

    today = _today_utc()

    today_day: MissionDay | None = None
    for day in mission.days:
        if day.date == today:
            today_day = day
            break

    if today_day is None:
        raise MissionGoneError("No mission day for today")

    # Mark day as complete (set cards_completed = cards_target)
    today_day.cards_completed = today_day.cards_target
    await db.flush()

    # Award XP for completing a mission day
    xp_amount = gamification_service.XP_RULES["daily_complete"]
    await gamification_service.award_xp(
        user_id=user_id,
        amount=xp_amount,
        source="daily_complete",
        db=db,
    )

    # Check if mission is fully complete (all days done)
    category_ids = [c.id for c in mission.categories]
    total_cards = await _count_cards_for_categories(category_ids, db)
    total_completed = sum(d.cards_completed for d in mission.days)

    if total_completed >= total_cards:
        mission.status = "completed"
        coverage = (total_completed / total_cards * 100) if total_cards > 0 else 0
        analytics_track(
            user_id=user_id,
            event="mission_completed",
            properties={
                "total_days": len(mission.days),
                "coverage_pct": round(coverage, 1),
            },
        )
    else:
        days_remaining = sum(1 for d in mission.days if d.date > today)
        analytics_track(
            user_id=user_id,
            event="mission_day_completed",
            properties={
                "day_number": today_day.day_number,
                "cards_done": today_day.cards_completed,
                "days_remaining": days_remaining,
            },
        )

    await db.flush()

    home_state_service.invalidate(user_id)

    return mission, today_day, xp_amount
