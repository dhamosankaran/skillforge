"""FSRS spaced-repetition study service.

All scheduling is performed server-side via py-fsrs (v6). The frontend
receives only `due_date`, `fsrs_state`, and scheduling metadata — it never
computes intervals.

State mapping (our DB string ↔ py-fsrs State enum):
  "new"        — no card_progress row yet; first review creates one
  "learning"   ↔ State.Learning   (value 1)
  "review"     ↔ State.Review     (value 2)
  "relearning" ↔ State.Relearning (value 3)

Fields tracked by us (not available on py-fsrs v6 Card):
  reps          — incremented on every non-Again rating
  lapses        — incremented on every Again (1) rating
  elapsed_days  — days between the previous review and the current one
  scheduled_days — days from current review to new due_date
  fsrs_step     — py-fsrs Card.step (learning/relearning step index; None for Review)
"""
import logging
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import redis
from fsrs import Card as FsrsCard, Rating, Scheduler, State
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.core.config import get_settings
from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.user import User
from app.schemas.study import DailyCardItem, DailyReviewResponse, ReviewResponse, StudyProgressResponse
from app.services import gamification_service, home_state_service
from app.utils.timezone import get_user_timezone

logger = logging.getLogger(__name__)

# Daily 5 = the size of the daily review queue. Crossing this count earns the
# `daily_complete` XP bonus exactly once per UTC day.
_DAILY_GOAL = 5

# Module-level scheduler — stateless, safe to share
_scheduler = Scheduler()

_DAILY_LIMIT = 5

_STATE_TO_FSRS: dict[str, State] = {
    "learning": State.Learning,
    "review": State.Review,
    "relearning": State.Relearning,
}
_FSRS_TO_STATE: dict[State, str] = {v: k for k, v in _STATE_TO_FSRS.items()}


# ── FSRS Card reconstruction ─────────────────────────────────────────────────


def _build_fsrs_card(progress: CardProgress) -> FsrsCard:
    """Reconstruct a py-fsrs Card from a stored CardProgress row.

    For state="new" (never reviewed), returns a fresh FsrsCard — py-fsrs
    treats new cards as Learning step=0, which is exactly right for a
    first review.
    """
    c = FsrsCard()
    if progress.state == "new":
        return c  # fresh card; py-fsrs handles the first review from scratch

    c.state = _STATE_TO_FSRS[progress.state]
    c.step = progress.fsrs_step  # None for Review, integer for Learning/Relearning
    c.stability = progress.stability if progress.stability > 0 else None
    c.difficulty = progress.difficulty_fsrs if progress.difficulty_fsrs > 0 else None
    c.due = progress.due_date
    c.last_review = progress.last_reviewed
    return c


def _apply_fsrs_result(
    progress: CardProgress,
    updated: FsrsCard,
    elapsed_days: float,
    now: datetime,
) -> None:
    """Write the py-fsrs review result back into the CardProgress ORM object.

    Called after `Scheduler.review_card` returns the updated FsrsCard.
    Does NOT flush — the caller is responsible for flushing the session.
    """
    progress.state = _FSRS_TO_STATE[updated.state]
    progress.fsrs_step = updated.step
    progress.stability = updated.stability or 0.0
    progress.difficulty_fsrs = updated.difficulty or 0.0
    progress.due_date = updated.due
    progress.last_reviewed = now
    progress.elapsed_days = round(elapsed_days, 4)

    # scheduled_days: fractional days from now to the new due_date
    delta = updated.due - now
    progress.scheduled_days = max(0.0, round(delta.total_seconds() / 86400, 4))


# ── Service errors ────────────────────────────────────────────────────────────


class CardNotFoundError(Exception):
    """Raised when the requested card_id does not exist."""

    def __init__(self, card_id: str) -> None:
        self.card_id = card_id
        super().__init__(f"Card {card_id!r} not found")


class CardForbiddenError(Exception):
    """Raised when the caller's plan does not permit access to the card."""

    def __init__(self, card_id: str) -> None:
        self.card_id = card_id
        super().__init__(f"Card {card_id!r} requires a Pro plan")


class DailyReviewLimitError(Exception):
    """Raised when a free user exceeds the daily 15-card review budget (spec #50)."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        super().__init__("Daily review limit reached")


# ── Daily-card review wall (spec #50) ─────────────────────────────────────────

_DAILY_CARD_LIMIT = 15
# 48h safety floor — longer than the widest plausible timezone swing
# (~14h between UTC-12 and UTC+14) plus headroom. The key's date advances
# at user-local midnight so old keys age out naturally.
_DAILY_CARD_KEY_TTL_SECONDS = 48 * 3600


def _utcnow() -> datetime:
    """Module-level seam for time-mocking in tests."""
    return datetime.now(timezone.utc)


def _get_redis() -> Optional[redis.Redis]:
    """Return a Redis client, or None if unavailable.

    Mirrors the pattern in ``home_state_service`` and
    ``geo_pricing_service`` — graceful degradation when Redis is offline
    so tests and dev without a Redis container still work.
    """
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        logger.debug("Redis unavailable — daily-card wall counter disabled")
        return None


def _next_local_midnight(now_utc: datetime, tz: ZoneInfo) -> datetime:
    """Next user-local midnight as a tz-aware datetime in the user's tz."""
    local_now = now_utc.astimezone(tz)
    tomorrow = (local_now + timedelta(days=1)).date()
    return datetime.combine(tomorrow, time(0, 0, 0), tzinfo=tz)


async def _check_daily_wall(user: User, db: AsyncSession) -> None:
    """Enforce the free-tier 15-card-per-day review wall (spec #50).

    Invariants:
      * Admins (``user.role == "admin"``) bypass unconditionally (AC-9).
      * Pro / Enterprise users skip the Redis call entirely — §Counter
        Scope Option 2 (AC-3).
      * Counter key is scoped to ``user.id + YYYY-MM-DD`` in the user's
        local timezone so midnight resets track the user's day.
      * Redis outage fails open: the review proceeds and the
        ``daily_card_submit`` event carries ``counter_unavailable=True``
        so the outage is still observable in PostHog.

    Raises:
        DailyReviewLimitError — free user's post-increment count exceeds
        the cap; caller must translate to HTTP 402 without mutating any
        FSRS / card_progress state.
    """
    if (user.role or "user") == "admin":
        return

    sub = user.subscription
    is_free = sub is None or sub.status != "active" or sub.plan == "free"
    if not is_free:
        return

    plan = sub.plan if sub is not None else "free"

    r = _get_redis()
    if r is None:
        analytics_track(
            user_id=user.id,
            event="daily_card_submit",
            properties={
                "plan": plan,
                "count_after": None,
                "was_walled": False,
                "counter_unavailable": True,
            },
        )
        logger.warning(
            "daily-card wall counter unavailable (redis down) for user %s", user.id
        )
        return

    now_utc = _utcnow()
    tz = await get_user_timezone(user.id, db)
    local_date = now_utc.astimezone(tz).date()
    key = f"daily_cards:{user.id}:{local_date.isoformat()}"

    try:
        count_after = r.incr(key)
        if count_after == 1:
            r.expire(key, _DAILY_CARD_KEY_TTL_SECONDS)
    except Exception:
        # Redis went away between ping and incr — fail open like the None path.
        analytics_track(
            user_id=user.id,
            event="daily_card_submit",
            properties={
                "plan": plan,
                "count_after": None,
                "was_walled": False,
                "counter_unavailable": True,
            },
        )
        logger.warning("daily-card INCR failed for user %s; failing open", user.id)
        return

    if count_after > _DAILY_CARD_LIMIT:
        resets_at = _next_local_midnight(now_utc, tz)
        analytics_track(
            user_id=user.id,
            event="daily_card_submit",
            properties={
                "plan": plan,
                "count_after": _DAILY_CARD_LIMIT,
                "was_walled": True,
                "counter_unavailable": False,
            },
        )
        raise DailyReviewLimitError(
            {
                "error": "free_tier_limit",
                "trigger": "daily_review",
                "cards_consumed": _DAILY_CARD_LIMIT,
                "cards_limit": _DAILY_CARD_LIMIT,
                "resets_at": resets_at.isoformat(),
            }
        )

    analytics_track(
        user_id=user.id,
        event="daily_card_submit",
        properties={
            "plan": plan,
            "count_after": count_after,
            "was_walled": False,
            "counter_unavailable": False,
        },
    )


# ── Public service methods ────────────────────────────────────────────────────


async def get_daily_review(
    user_id: str,
    is_free: bool,
    db: AsyncSession,
) -> DailyReviewResponse:
    """Return up to 5 cards due for review for the given user.

    Queue-building algorithm (two-pass):
      1. Overdue cards — card_progress rows where due_date <= now, ordered
         by due_date ASC (most overdue first). Capped at DAILY_LIMIT.
      2. Fill remaining slots with unreviewed cards (no card_progress row
         for this user), ordered by cards.created_at ASC.

    Free-plan users see only cards from categories where source="foundation".
    Pro/enterprise users see cards from all categories.
    """
    now = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())

    # ── Pass 1: overdue progress rows ────────────────────────────────────────
    stmt = (
        select(CardProgress, Card, Category)
        .join(Card, Card.id == CardProgress.card_id)
        .join(Category, Category.id == Card.category_id)
        .where(CardProgress.user_id == user_id)
        .where(CardProgress.state != "new")
        .where(CardProgress.due_date <= now)
        .order_by(CardProgress.due_date.asc())
        .limit(_DAILY_LIMIT)
    )
    if is_free:
        stmt = stmt.where(Category.source == "foundation")

    overdue_rows = (await db.execute(stmt)).all()

    result: list[DailyCardItem] = []
    for row in overdue_rows:
        cp, card, cat = row.CardProgress, row.Card, row.Category
        result.append(
            DailyCardItem(
                card_id=card.id,
                question=card.question,
                answer=card.answer,
                difficulty=card.difficulty,
                tags=card.tags or [],
                category_id=cat.id,
                category_name=cat.name,
                fsrs_state=cp.state,
                due_date=cp.due_date,
                reps=cp.reps,
                lapses=cp.lapses,
            )
        )

    # ── Pass 2: fill with unreviewed cards ───────────────────────────────────
    remaining = _DAILY_LIMIT - len(result)
    if remaining > 0:
        # Subquery: card IDs this user already has a progress row for
        reviewed_ids_sq = (
            select(CardProgress.card_id)
            .where(CardProgress.user_id == user_id)
            .scalar_subquery()
        )
        new_stmt = (
            select(Card, Category)
            .join(Category, Category.id == Card.category_id)
            .where(Card.id.not_in(reviewed_ids_sq))
            .order_by(Card.created_at.asc())
            .limit(remaining)
        )
        if is_free:
            new_stmt = new_stmt.where(Category.source == "foundation")

        new_rows = (await db.execute(new_stmt)).all()
        for row in new_rows:
            card, cat = row.Card, row.Category
            result.append(
                DailyCardItem(
                    card_id=card.id,
                    question=card.question,
                    answer=card.answer,
                    difficulty=card.difficulty,
                    tags=card.tags or [],
                    category_id=cat.id,
                    category_name=cat.name,
                    fsrs_state="new",
                    due_date=None,
                    reps=0,
                    lapses=0,
                )
            )

    # B-019 — completed_today. Uses the same UTC today-start window as the
    # `daily_complete` XP bonus path below (~line 540) so the widget flip
    # and the XP award share one definition of "done for today." The
    # library-size clamp lets users whose foundation pool is smaller than
    # _DAILY_GOAL still reach a completed state — the stable-within-a-day
    # pool size is `reviewed_today + len(current_queue)` because every
    # reviewed card leaves the queue, so the sum stays constant as the
    # user progresses.
    today_start_utc = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    reviewed_today = (
        await db.execute(
            select(sa_func.count(CardProgress.id))
            .where(CardProgress.user_id == user_id)
            .where(CardProgress.last_reviewed >= today_start_utc)
        )
    ).scalar_one()
    daily_pool_today = reviewed_today + len(result)
    completion_threshold = min(_DAILY_GOAL, daily_pool_today)
    completed_today = reviewed_today >= completion_threshold and completion_threshold > 0

    return DailyReviewResponse(
        cards=result,
        total_due=len(result),
        session_id=session_id,
        completed_today=completed_today,
    )


async def create_progress(
    user_id: str,
    card_id: str,
    db: AsyncSession,
) -> CardProgress:
    """Create an initial card_progress row with state='new'.

    Use this to explicitly pre-create a progress record before the first
    review (e.g., when the card is added to a user's deck). `review_card`
    also creates the row implicitly on first review, so calling this first
    is optional.
    """
    progress = CardProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        card_id=card_id,
        state="new",
        stability=0.0,
        difficulty_fsrs=0.0,
        elapsed_days=0.0,
        scheduled_days=0.0,
        reps=0,
        lapses=0,
    )
    db.add(progress)
    await db.flush()
    return progress


async def review_card(
    user_id: str,
    card_id: str,
    rating: int,
    is_free: bool,
    db: AsyncSession,
    time_spent_ms: int = 0,
    session_id: Optional[str] = None,
    user: Optional[User] = None,
) -> ReviewResponse:
    """Apply a FSRS review rating to a card.

    Creates the card_progress row on first review; updates it thereafter.
    Returns the new scheduling state so the caller can display the next
    due date.

    Raises:
        CardNotFoundError     — card_id does not exist in the cards table
        CardForbiddenError    — card's category is not accessible under the
                                caller's plan (free user + non-foundation card)
        DailyReviewLimitError — free user has exceeded the daily 15-card
                                review budget (spec #50). Only raised when
                                ``user`` is provided so legacy callers
                                without a User object skip the wall.
    """
    now = datetime.now(timezone.utc)

    # ── Validate card + plan gate ────────────────────────────────────────────
    card_row = (
        await db.execute(
            select(Card, Category)
            .join(Category, Category.id == Card.category_id)
            .where(Card.id == card_id)
        )
    ).first()

    if card_row is None:
        raise CardNotFoundError(card_id)

    card, category = card_row.Card, card_row.Category
    if is_free and category.source != "foundation":
        raise CardForbiddenError(card_id)

    # ── Daily-card review wall (spec #50) ────────────────────────────────────
    # Runs AFTER the plan-gate check and BEFORE any FSRS or card_progress
    # mutation so a walled submit leaves every row untouched.
    if user is not None:
        await _check_daily_wall(user, db)

    # ── Load or create progress row ──────────────────────────────────────────
    progress = (
        await db.execute(
            select(CardProgress)
            .where(CardProgress.user_id == user_id)
            .where(CardProgress.card_id == card_id)
        )
    ).scalar_one_or_none()

    if progress is None:
        progress = CardProgress(
            id=str(uuid.uuid4()),
            user_id=user_id,
            card_id=card_id,
            state="new",
            stability=0.0,
            difficulty_fsrs=0.0,
            elapsed_days=0.0,
            scheduled_days=0.0,
            reps=0,
            lapses=0,
        )
        db.add(progress)

    # ── Compute elapsed_days (time since last review) ────────────────────────
    if progress.last_reviewed is not None and progress.state != "new":
        elapsed_days = (now - progress.last_reviewed).total_seconds() / 86400
    else:
        elapsed_days = 0.0

    # ── Reconstruct py-fsrs Card and apply review ────────────────────────────
    fsrs_card = _build_fsrs_card(progress)
    fsrs_rating = Rating(rating)
    updated_card, _ = _scheduler.review_card(
        fsrs_card, fsrs_rating, review_datetime=now
    )

    # ── Track reps / lapses (py-fsrs v6 does not expose these) ──────────────
    if fsrs_rating == Rating.Again:
        progress.lapses += 1
    else:
        progress.reps += 1

    # ── Write result back to ORM object ─────────────────────────────────────
    _apply_fsrs_result(progress, updated_card, elapsed_days, now)

    await db.flush()

    analytics_track(
        user_id=user_id,
        event="card_reviewed",
        properties={
            "card_id": card_id,
            "rating": rating,
            "time_spent_ms": time_spent_ms,
            "fsrs_state": progress.state,
            "reps": progress.reps,
            "lapses": progress.lapses,
        },
    )

    # ── Gamification: per-review XP + streak tick ───────────────────────────
    # award_xp internally calls update_streak, so the streak is bumped on the
    # first XP-earning activity of the day. We don't need a separate
    # update_streak call here.
    await gamification_service.award_xp(
        user_id=user_id,
        amount=gamification_service.XP_RULES["review"],
        source="review",
        db=db,
    )

    # ── Daily 5 completion bonus ────────────────────────────────────────────
    # Count distinct cards reviewed today (UTC). When this review is the one
    # that takes the count from 4 → 5, award the bonus exactly once. A 6th
    # review on the same day finds count == 6 and skips, so the bonus never
    # double-fires.
    from sqlalchemy import func as sa_func
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    reviewed_today = (
        await db.execute(
            select(sa_func.count(CardProgress.id))
            .where(CardProgress.user_id == user_id)
            .where(CardProgress.last_reviewed >= today_start)
        )
    ).scalar_one()
    if reviewed_today == _DAILY_GOAL:
        await gamification_service.award_xp(
            user_id=user_id,
            amount=gamification_service.XP_RULES["daily_complete"],
            source="daily_complete",
            db=db,
        )

    home_state_service.invalidate(user_id)

    return ReviewResponse(
        card_id=card_id,
        fsrs_state=progress.state,
        stability=progress.stability,
        difficulty=progress.difficulty_fsrs,
        due_date=progress.due_date,
        reps=progress.reps,
        lapses=progress.lapses,
        scheduled_days=progress.scheduled_days,
    )


async def get_progress(
    user_id: str,
    db: AsyncSession,
) -> StudyProgressResponse:
    """Return aggregate study statistics for the caller.

    Counts card_progress rows by state, and sums reps and lapses.
    Cards the user has never touched have no card_progress row and are not
    counted here (they show up as "unreviewed" in the daily queue instead).
    """
    from sqlalchemy import func as sa_func

    rows = (
        await db.execute(
            select(
                CardProgress.state,
                sa_func.count(CardProgress.id).label("cnt"),
                sa_func.coalesce(sa_func.sum(CardProgress.reps), 0).label("reps"),
                sa_func.coalesce(sa_func.sum(CardProgress.lapses), 0).label("lapses"),
            )
            .where(CardProgress.user_id == user_id)
            .group_by(CardProgress.state)
        )
    ).all()

    by_state: dict[str, int] = {"new": 0, "learning": 0, "review": 0, "relearning": 0}
    total_reps = 0
    total_lapses = 0

    for row in rows:
        by_state[row.state] = row.cnt
        total_reps += row.reps
        total_lapses += row.lapses

    total_reviewed = by_state["learning"] + by_state["review"] + by_state["relearning"]

    return StudyProgressResponse(
        total_reviewed=total_reviewed,
        by_state=by_state,
        total_reps=total_reps,
        total_lapses=total_lapses,
    )
