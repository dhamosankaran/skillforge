"""Gamification service — XP, streaks, badges.

Public API:
  - award_xp(user_id, amount, source, db) — credit XP, evaluate badges
  - update_streak(user_id, db)             — bump or reset streak based on
                                               last_active_date vs today (UTC)
  - get_stats(user_id, db)                  — read current stats + badges

The badge catalog is defined in-module (BADGES) and mirrors the seed inserted
by the alembic migration `802d5ba2e219_add_gamification_tables`. Keep both in
sync if a badge is added or removed.

XP is the source of truth for "I did something gamifiable today" — every call
to `award_xp` also calls `update_streak` so callers don't need to remember to
do it themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.gamification import Badge, GamificationStats, UserBadge

# ── XP rule table ────────────────────────────────────────────────────────────

XPSource = Literal["review", "quiz", "daily_complete"]

XP_RULES: dict[str, int] = {
    "review": 10,
    "quiz": 25,
    "daily_complete": 50,
}


# ── Badge catalog (mirrors alembic seed) ─────────────────────────────────────


@dataclass(frozen=True)
class BadgeDef:
    id: str
    name: str
    threshold_type: str  # "xp" | "streak" | "event"
    threshold_value: int


BADGES: tuple[BadgeDef, ...] = (
    BadgeDef("first_review", "First Step", "event", 0),
    BadgeDef("streak_3", "On a Roll", "streak", 3),
    BadgeDef("streak_7", "One Week Strong", "streak", 7),
    BadgeDef("streak_30", "Habit Formed", "streak", 30),
    BadgeDef("streak_100", "Centurion", "streak", 100),
    BadgeDef("xp_100", "Apprentice", "xp", 100),
    BadgeDef("xp_500", "Journeyman", "xp", 500),
    BadgeDef("xp_2000", "Expert", "xp", 2000),
    BadgeDef("xp_10000", "Master", "xp", 10000),
)


# ── Errors ───────────────────────────────────────────────────────────────────


class InvalidXPSourceError(ValueError):
    """Raised when `source` is not one of XP_RULES keys."""


# ── Internal helpers ─────────────────────────────────────────────────────────


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


async def _get_or_create_stats(
    user_id: str, db: AsyncSession
) -> GamificationStats:
    """Return the user's stats row, creating a zeroed one on first access."""
    stats = await db.get(GamificationStats, user_id)
    if stats is None:
        stats = GamificationStats(
            user_id=user_id,
            current_streak=0,
            longest_streak=0,
            total_xp=0,
            last_active_date=None,
            freezes_available=0,
            freeze_week_start=None,
        )
        db.add(stats)
        await db.flush()
    return stats


async def _evaluate_badges(
    stats: GamificationStats,
    source: XPSource | None,
    db: AsyncSession,
) -> list[str]:
    """Award any badges whose threshold is now met. Returns newly-earned ids.

    Re-evaluation is idempotent because of the `(user_id, badge_id)` unique
    constraint and the existence check below.
    """
    earned = (
        await db.execute(
            select(UserBadge.badge_id).where(UserBadge.user_id == stats.user_id)
        )
    ).scalars().all()
    earned_set = set(earned)

    newly: list[str] = []
    for b in BADGES:
        if b.id in earned_set:
            continue
        ok = False
        if b.threshold_type == "xp":
            ok = stats.total_xp >= b.threshold_value
        elif b.threshold_type == "streak":
            ok = stats.current_streak >= b.threshold_value
        elif b.threshold_type == "event":
            # Currently the only "event" badge is `first_review`.
            ok = b.id == "first_review" and source == "review"
        if ok:
            db.add(UserBadge(user_id=stats.user_id, badge_id=b.id))
            newly.append(b.id)
            analytics_track(
                user_id=stats.user_id,
                event="badge_earned",
                properties={"badge_id": b.id, "badge_name": b.name},
            )

    if newly:
        await db.flush()
    return newly


# ── Public API ───────────────────────────────────────────────────────────────


async def update_streak(user_id: str, db: AsyncSession) -> GamificationStats:
    """Bump the streak for today's first qualifying activity.

    Rules:
      - last_active_date == today           → no-op (already counted)
      - last_active_date == yesterday       → current_streak += 1
      - last_active_date older or NULL      → current_streak = 1
    Always updates `last_active_date = today` and `longest_streak`.
    """
    stats = await _get_or_create_stats(user_id, db)
    today = _today_utc()

    if stats.last_active_date == today:
        return stats  # already counted today

    yesterday = today - timedelta(days=1)
    previous = stats.current_streak
    if stats.last_active_date == yesterday:
        stats.current_streak += 1
    else:
        stats.current_streak = 1

    stats.last_active_date = today
    if stats.current_streak > stats.longest_streak:
        stats.longest_streak = stats.current_streak

    await db.flush()

    analytics_track(
        user_id=user_id,
        event="streak_incremented",
        properties={"new_length": stats.current_streak, "previous": previous},
    )
    return stats


async def reset_streak_if_missed(
    user_id: str, db: AsyncSession
) -> GamificationStats:
    """Lazy-reset: if last_active_date is older than yesterday, zero the streak.

    Used by both the nightly job and on-read so users see correct values even
    if the cron has not run yet. Pro freeze logic is the responsibility of the
    nightly job; this function is the simple non-Pro path.
    """
    stats = await _get_or_create_stats(user_id, db)
    if stats.last_active_date is None or stats.current_streak == 0:
        return stats

    today = _today_utc()
    yesterday = today - timedelta(days=1)
    if stats.last_active_date < yesterday:
        previous = stats.current_streak
        stats.current_streak = 0
        await db.flush()
        analytics_track(
            user_id=user_id,
            event="streak_broken",
            properties={"previous_length": previous},
        )
    return stats


async def award_xp(
    user_id: str,
    amount: int,
    source: XPSource,
    db: AsyncSession,
) -> tuple[GamificationStats, list[str]]:
    """Credit XP, bump the streak, and evaluate badges in one transaction.

    Returns (stats, newly_earned_badge_ids). The `amount` is validated against
    the rule table — passing the wrong number for the source raises ValueError
    so the server stays the source of truth for XP economy.
    """
    if source not in XP_RULES:
        raise InvalidXPSourceError(f"unknown XP source: {source!r}")
    if amount != XP_RULES[source]:
        raise InvalidXPSourceError(
            f"amount {amount} does not match rule for {source!r} "
            f"(expected {XP_RULES[source]})"
        )

    stats = await _get_or_create_stats(user_id, db)
    stats.total_xp += amount
    await db.flush()

    # Streak ticks on every XP-earning action; the function itself is a no-op
    # if the user has already been counted today.
    await update_streak(user_id, db)

    newly = await _evaluate_badges(stats, source, db)

    analytics_track(
        user_id=user_id,
        event="xp_awarded",
        properties={
            "amount": amount,
            "source_type": source,
            "total_xp_after": stats.total_xp,
        },
    )
    return stats, newly


@dataclass
class StatsView:
    """Plain read-model returned by `get_stats` (decoupled from ORM)."""

    user_id: str
    current_streak: int
    longest_streak: int
    total_xp: int
    last_active_date: date | None
    freezes_available: int
    badges: list[dict]


async def get_stats(user_id: str, db: AsyncSession) -> StatsView:
    """Return the user's current stats plus the list of earned badges.

    Performs a lazy streak-reset on read so callers always see the correct
    streak value even between nightly job runs.
    """
    await reset_streak_if_missed(user_id, db)
    stats = await _get_or_create_stats(user_id, db)

    rows = (
        await db.execute(
            select(UserBadge, Badge)
            .join(Badge, Badge.id == UserBadge.badge_id)
            .where(UserBadge.user_id == user_id)
            .order_by(UserBadge.earned_at.asc())
        )
    ).all()

    badges = [
        {
            "badge_id": ub.UserBadge.badge_id,
            "name": ub.Badge.name,
            "earned_at": ub.UserBadge.earned_at,
        }
        for ub in rows
    ]

    return StatsView(
        user_id=stats.user_id,
        current_streak=stats.current_streak,
        longest_streak=stats.longest_streak,
        total_xp=stats.total_xp,
        last_active_date=stats.last_active_date,
        freezes_available=stats.freezes_available,
        badges=badges,
    )
