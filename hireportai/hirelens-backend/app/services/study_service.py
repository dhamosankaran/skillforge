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
import uuid
from datetime import datetime, timezone
from typing import Optional

from fsrs import Card as FsrsCard, Rating, Scheduler, State
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.schemas.study import DailyCardItem, DailyReviewResponse, ReviewResponse, StudyProgressResponse
from app.services import gamification_service

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

    return DailyReviewResponse(
        cards=result,
        total_due=len(result),
        session_id=session_id,
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
) -> ReviewResponse:
    """Apply a FSRS review rating to a card.

    Creates the card_progress row on first review; updates it thereafter.
    Returns the new scheduling state so the caller can display the next
    due date.

    Raises:
        CardNotFoundError  — card_id does not exist in the cards table
        CardForbiddenError — card's category is not accessible under the
                             caller's plan (free user + non-foundation card)
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
