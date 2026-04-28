"""FSRS spaced-repetition study service for Phase 6 quiz_items.

New file per spec 6.2 D-1 — does NOT extend `study_service.py`. The
legacy card-based study path (`study_service.py`) and this quiz-item
path coexist until slice 6.15 cleanup retires the former via
`git rm`. FSRS reconstruction helpers (`_build_fsrs_quiz_card`,
`_apply_fsrs_result_to_quiz_item`) are byte-equivalent to
`study_service._build_fsrs_card` / `_apply_fsrs_result` modulo the FK
swap (card_id → quiz_item_id, card_progress → quiz_item_progress) per
D-2.

Differences from `study_service`:
  - No plan-gate at the service layer (slice 6.7 owns persona-aware
    composition and `decks.tier` gating).
  - No daily-card review wall (D-4 — write-side wall enforcement is
    deferred to a follow-up slice). `_compute_daily_quiz_status`
    returns the permissive sentinel only.
  - No XP / streak / gamification call-out (D-7).
  - Retired-quiz_item guard: a review against a retired quiz_item
    with no existing progress row raises `QuizItemRetiredError` (HTTP
    409). Existing progress rows continue to receive updates.
  - Archive guard: lesson or deck `archived_at IS NOT NULL` raises
    `QuizItemForbiddenError` (HTTP 403).

Spec: docs/specs/phase-6/02-fsrs-quiz-item-binding.md
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fsrs import Card as FsrsCard, Rating, Scheduler, State
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.quiz_item_progress import QuizItemProgress
from app.models.user import User
from app.schemas.analytics_event import QuizReviewEventCreate
from app.schemas.quiz_item import (
    DailyQuizItem,
    DailyQuizReviewResponse,
    QuizProgressResponse,
    QuizReviewResponse,
)
from app.schemas.study import DailyStatus
from app.services import analytics_event_service
from app.utils.timezone import get_user_timezone

logger = logging.getLogger(__name__)

# Daily 5 = the size of the daily review queue. Matches
# `study_service._DAILY_GOAL` per OQ-1 / D-3.
_DAILY_GOAL = 5

# Module-level scheduler — stateless, safe to share. Mirrors
# `study_service.py:48` per D-2.
_scheduler = Scheduler()

_STATE_TO_FSRS: dict[str, State] = {
    "learning": State.Learning,
    "review": State.Review,
    "relearning": State.Relearning,
}
_FSRS_TO_STATE: dict[State, str] = {v: k for k, v in _STATE_TO_FSRS.items()}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _utcnow() -> datetime:
    """Module-level seam for time-mocking in tests."""
    return datetime.now(timezone.utc)


def _next_local_midnight(now_utc: datetime, tz: ZoneInfo) -> datetime:
    """Next user-local midnight as a tz-aware datetime in the user's tz.

    Duplicated from `study_service.py:168` per OQ-3 — kept local so
    slice 6.15 cleanup can `git rm` this file without touching
    `study_service`.
    """
    local_now = now_utc.astimezone(tz)
    tomorrow = (local_now + timedelta(days=1)).date()
    return datetime.combine(tomorrow, time(0, 0, 0), tzinfo=tz)


# ── FSRS Card reconstruction (byte-equivalent to study_service) ─────────────


def _build_fsrs_quiz_card(progress: QuizItemProgress) -> FsrsCard:
    """Reconstruct a py-fsrs Card from a stored QuizItemProgress row.

    For state="new" (never reviewed), returns a fresh FsrsCard — py-fsrs
    treats new cards as Learning step=0, which is exactly right for a
    first review. Mirrors `study_service._build_fsrs_card`.
    """
    c = FsrsCard()
    if progress.state == "new":
        return c

    c.state = _STATE_TO_FSRS[progress.state]
    c.step = progress.fsrs_step
    c.stability = progress.stability if progress.stability > 0 else None
    c.difficulty = progress.difficulty_fsrs if progress.difficulty_fsrs > 0 else None
    c.due = progress.due_date
    c.last_review = progress.last_reviewed
    return c


def _apply_fsrs_result_to_quiz_item(
    progress: QuizItemProgress,
    updated: FsrsCard,
    elapsed_days: float,
    now: datetime,
) -> None:
    """Write the py-fsrs review result back into the QuizItemProgress row.

    Called after `Scheduler.review_card` returns the updated FsrsCard.
    Does NOT flush — the caller is responsible for flushing the session.
    Mirrors `study_service._apply_fsrs_result`.
    """
    progress.state = _FSRS_TO_STATE[updated.state]
    progress.fsrs_step = updated.step
    progress.stability = updated.stability or 0.0
    progress.difficulty_fsrs = updated.difficulty or 0.0
    progress.due_date = updated.due
    progress.last_reviewed = now
    progress.elapsed_days = round(elapsed_days, 4)

    delta = updated.due - now
    progress.scheduled_days = max(0.0, round(delta.total_seconds() / 86400, 4))


# ── Service errors ───────────────────────────────────────────────────────────


class QuizItemNotFoundError(Exception):
    """Raised when the requested quiz_item_id does not exist."""

    def __init__(self, quiz_item_id: str) -> None:
        self.quiz_item_id = quiz_item_id
        super().__init__(f"Quiz item {quiz_item_id!r} not found")


class QuizItemForbiddenError(Exception):
    """Raised when the requesting user is forbidden from acting on the quiz_item.

    Slice 6.2 originally covered the archive-guard (lesson/deck archived);
    slice 6.5 §12 D-2 reuses it for the tier-mismatch path (free user on
    a premium deck) — `reason='premium_deck'` makes the message accurate
    without changing the route's existing 403 mapping.
    """

    def __init__(self, quiz_item_id: str, *, reason: str = "archived") -> None:
        self.quiz_item_id = quiz_item_id
        self.reason = reason
        if reason == "premium_deck":
            message = (
                f"Quiz item {quiz_item_id!r} is in a premium deck; "
                f"upgrade required"
            )
        else:
            message = f"Quiz item {quiz_item_id!r} is in an archived lesson or deck"
        super().__init__(message)


class QuizItemRetiredError(Exception):
    """Raised when a NEW review is attempted against a retired quiz_item.

    Existing `quiz_item_progress` rows continue to receive updates so a
    user mid-review-session on a quiz_item retired between fetch and
    submit doesn't lose their FSRS history.
    """

    def __init__(self, quiz_item_id: str) -> None:
        self.quiz_item_id = quiz_item_id
        super().__init__(
            f"Quiz item {quiz_item_id!r} is retired; no new reviews accepted"
        )


class QuizItemNotVisibleError(Exception):
    """Raised when the requesting user's persona excludes the quiz_item's deck.

    Slice 6.5 §12 D-7: 404 across all read paths for persona-visibility
    mismatch (information-leakage minimization). Route maps to 404.
    """

    def __init__(self, quiz_item_id: str) -> None:
        self.quiz_item_id = quiz_item_id
        super().__init__(
            f"Quiz item {quiz_item_id!r} is not visible to the requesting user"
        )


# ── Read-time visibility helpers (slice 6.5 §6.3 / D-5 — duplicated to
# `lesson_service.py`) ────────────────────────────────────────────────────────


def _persona_visible_to(deck_persona: str, user_persona: Optional[str]) -> bool:
    """True iff a user with ``user_persona`` may see a deck with
    ``persona_visibility == deck_persona``. Mirrors deck_admin_service
    semantics: ``'both'`` is visible to everyone; the named persona is
    visible only to a user with that persona.
    """
    if deck_persona == "both":
        return True
    if user_persona is None:
        return False
    return deck_persona == user_persona


def _visible_persona_set(user: Optional[User]) -> tuple[str, ...]:
    """``Deck.persona_visibility`` values the user is allowed to see.

    Persona-null users see only ``'both'``; persona-set users see
    ``'both'`` + their persona.
    """
    if user is None or user.persona is None:
        return ("both",)
    return ("both", user.persona)


def _allowed_tiers_for_user(user: Optional[User]) -> tuple[str, ...]:
    """``Deck.tier`` values the user can access given their plan (D-2).

    Free users (and persona-null / unloaded-subscription) see only
    ``'foundation'``; paid plans see ``'foundation'`` + ``'premium'``.
    """
    plan = _resolve_plan(user)
    if plan and plan != "free":
        return ("foundation", "premium")
    return ("foundation",)


# ── Daily-status read (spec 6.2 §4.4 / §7 — sentinel only per D-4) ──────────


async def _compute_daily_quiz_status(user: User, db: AsyncSession) -> DailyStatus:
    """Read-side mirror of the (deferred) quiz_item review wall.

    Slice 6.2 ships the permissive sentinel unconditionally — the
    write-side wall lands in a follow-up slice. The field is reserved
    on `DailyQuizReviewResponse` so 6.3 FE consumers don't churn when
    the wall lands.
    """
    now_utc = _utcnow()
    tz = await get_user_timezone(user.id, db)
    resets_at = _next_local_midnight(now_utc, tz)
    return DailyStatus(
        cards_consumed=0,
        cards_limit=-1,
        can_review=True,
        resets_at=resets_at,
    )


# ── Public service methods ───────────────────────────────────────────────────


async def get_daily_quiz_items(
    user_id: str,
    db: AsyncSession,
    *,
    user: Optional[User] = None,
) -> DailyQuizReviewResponse:
    """Return up to _DAILY_GOAL quiz_items due for review.

    Two-pass queue (mirrors `study_service.get_daily_review`):
      1. Overdue progress rows (due_date <= now), ordered by due_date ASC.
      2. Fresh-fill with unreviewed quiz_items, ordered by created_at ASC.

    Excludes retired quiz_items, archived lessons, and archived decks.
    No plan gate (slice 6.7 owns persona/decks.tier composition).
    """
    now = _utcnow()
    session_id = str(uuid.uuid4())

    # Slice 6.5 §6.1.1 — persona-visibility (D-3) + tier (D-2) filters block
    # premium / persona-narrowed decks at queue inclusion. Free-user-on-
    # premium-deck quiz_items never surface in the queue; if the user holds
    # a stored quiz_item_id, R-2 raises 403 post-load.
    visible_personas = _visible_persona_set(user)
    allowed_tiers = _allowed_tiers_for_user(user)

    # ── Pass 1: overdue progress rows ────────────────────────────────────────
    overdue_stmt = (
        select(QuizItemProgress, QuizItem, Lesson, Deck)
        .join(QuizItem, QuizItem.id == QuizItemProgress.quiz_item_id)
        .join(Lesson, Lesson.id == QuizItem.lesson_id)
        .join(Deck, Deck.id == Lesson.deck_id)
        .where(QuizItemProgress.user_id == user_id)
        .where(QuizItemProgress.state != "new")
        .where(QuizItemProgress.due_date <= now)
        .where(QuizItem.retired_at.is_(None))
        .where(Lesson.archived_at.is_(None))
        .where(Deck.archived_at.is_(None))
        .where(Deck.persona_visibility.in_(visible_personas))
        .where(Deck.tier.in_(allowed_tiers))
        .order_by(QuizItemProgress.due_date.asc())
        .limit(_DAILY_GOAL)
    )

    overdue_rows = (await db.execute(overdue_stmt)).all()

    result: list[DailyQuizItem] = []
    for row in overdue_rows:
        qip, qi, lesson, deck = (
            row.QuizItemProgress,
            row.QuizItem,
            row.Lesson,
            row.Deck,
        )
        result.append(
            DailyQuizItem(
                quiz_item_id=qi.id,
                lesson_id=lesson.id,
                lesson_title=lesson.title,
                deck_id=deck.id,
                deck_slug=deck.slug,
                question=qi.question,
                answer=qi.answer,
                question_type=qi.question_type,
                distractors=qi.distractors,
                difficulty=qi.difficulty,
                fsrs_state=qip.state,
                due_date=qip.due_date,
                reps=qip.reps,
                lapses=qip.lapses,
            )
        )

    # ── Pass 2: fresh-fill with unreviewed quiz_items ────────────────────────
    remaining = _DAILY_GOAL - len(result)
    if remaining > 0:
        reviewed_ids_sq = (
            select(QuizItemProgress.quiz_item_id)
            .where(QuizItemProgress.user_id == user_id)
            .scalar_subquery()
        )
        new_stmt = (
            select(QuizItem, Lesson, Deck)
            .join(Lesson, Lesson.id == QuizItem.lesson_id)
            .join(Deck, Deck.id == Lesson.deck_id)
            .where(QuizItem.id.not_in(reviewed_ids_sq))
            .where(QuizItem.retired_at.is_(None))
            .where(Lesson.archived_at.is_(None))
            .where(Deck.archived_at.is_(None))
            .where(Deck.persona_visibility.in_(visible_personas))
            .where(Deck.tier.in_(allowed_tiers))
            .order_by(QuizItem.created_at.asc())
            .limit(remaining)
        )

        new_rows = (await db.execute(new_stmt)).all()
        for row in new_rows:
            qi, lesson, deck = row.QuizItem, row.Lesson, row.Deck
            result.append(
                DailyQuizItem(
                    quiz_item_id=qi.id,
                    lesson_id=lesson.id,
                    lesson_title=lesson.title,
                    deck_id=deck.id,
                    deck_slug=deck.slug,
                    question=qi.question,
                    answer=qi.answer,
                    question_type=qi.question_type,
                    distractors=qi.distractors,
                    difficulty=qi.difficulty,
                    fsrs_state="new",
                    due_date=None,
                    reps=0,
                    lapses=0,
                )
            )

    daily_status = (
        await _compute_daily_quiz_status(user, db)
        if user is not None
        else DailyStatus(
            cards_consumed=0,
            cards_limit=-1,
            can_review=True,
            resets_at=datetime(1970, 1, 1, tzinfo=timezone.utc),
        )
    )

    return DailyQuizReviewResponse(
        quiz_items=result,
        total_due=len(result),
        session_id=session_id,
        daily_status=daily_status,
    )


async def review_quiz_item(
    user_id: str,
    quiz_item_id: str,
    rating: int,
    db: AsyncSession,
    time_spent_ms: int = 0,
    session_id: Optional[str] = None,
    user: Optional[User] = None,
) -> QuizReviewResponse:
    """Apply a FSRS review rating to a quiz_item.

    Creates the quiz_item_progress row on first review; updates it
    thereafter. Mirrors `study_service.review_card` modulo D-1/D-4/D-7
    differences (no plan gate, no wall, no XP).

    Raises:
        QuizItemNotFoundError  — quiz_item_id does not exist.
        QuizItemForbiddenError — lesson or deck is archived.
        QuizItemRetiredError   — quiz_item is retired AND no existing
                                 progress row (HTTP 409).
    """
    now = _utcnow()

    # ── Validate quiz_item + load lesson + deck for archive guard ────────────
    qi_row = (
        await db.execute(
            select(QuizItem, Lesson, Deck)
            .join(Lesson, Lesson.id == QuizItem.lesson_id)
            .join(Deck, Deck.id == Lesson.deck_id)
            .where(QuizItem.id == quiz_item_id)
        )
    ).first()

    if qi_row is None:
        raise QuizItemNotFoundError(quiz_item_id)

    qi, lesson, deck = qi_row.QuizItem, qi_row.Lesson, qi_row.Deck

    if lesson.archived_at is not None or deck.archived_at is not None:
        raise QuizItemForbiddenError(quiz_item_id)

    # Slice 6.5 §6.1.2 — persona-visibility check (D-3 / D-7). 404 across all
    # read paths for persona mismatch (information-leakage minimization).
    user_persona = user.persona if user is not None else None
    if not _persona_visible_to(deck.persona_visibility, user_persona):
        raise QuizItemNotVisibleError(quiz_item_id)

    # Slice 6.5 §6.1.2 — tier check (D-2). Premium deck + free user → 403.
    # The deck exists and the user can access it post-upgrade, so 403 is
    # semantically distinct from the 404-on-persona path above.
    if deck.tier not in _allowed_tiers_for_user(user):
        raise QuizItemForbiddenError(quiz_item_id, reason="premium_deck")

    # ── Load existing progress row (if any) ──────────────────────────────────
    progress = (
        await db.execute(
            select(QuizItemProgress)
            .where(QuizItemProgress.user_id == user_id)
            .where(QuizItemProgress.quiz_item_id == quiz_item_id)
        )
    ).scalar_one_or_none()

    # ── Retired-quiz guard. Block NEW progress rows; allow updates to
    # existing rows so mid-session retirement doesn't lose history. ──────────
    if qi.retired_at is not None and progress is None:
        raise QuizItemRetiredError(quiz_item_id)

    is_first_review = progress is None
    if progress is None:
        progress = QuizItemProgress(
            id=str(uuid.uuid4()),
            user_id=user_id,
            quiz_item_id=quiz_item_id,
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
    fsrs_card = _build_fsrs_quiz_card(progress)
    fsrs_rating = Rating(rating)
    updated_card, _ = _scheduler.review_card(
        fsrs_card, fsrs_rating, review_datetime=now
    )

    # ── Track reps / lapses (py-fsrs v6 does not expose these) ──────────────
    if fsrs_rating == Rating.Again:
        progress.lapses += 1
    else:
        progress.reps += 1

    # ── Write result back to ORM object ──────────────────────────────────────
    _apply_fsrs_result_to_quiz_item(progress, updated_card, elapsed_days, now)

    await db.flush()

    # ── Analytics. Per spec §8: progress_initialized fires only on first
    # review (creates the row); reviewed fires on every review. ──────────────
    plan = _resolve_plan(user)
    persona = user.persona if user is not None else None
    analytics_props_common: dict[str, Any] = {
        "quiz_item_id": quiz_item_id,
        "lesson_id": lesson.id,
        "deck_id": deck.id,
        "plan": plan,
        "persona": persona,
    }

    fsrs_state_before = "new" if is_first_review else _state_before(progress, fsrs_card)

    if is_first_review:
        try:
            analytics_track(
                user_id=user_id,
                event="quiz_item_progress_initialized",
                properties=dict(analytics_props_common),
            )
        except Exception:
            # D-7: analytics never blocks the user-blocking critical path.
            logger.exception("analytics_track_failed for quiz_item_progress_initialized")

    try:
        analytics_track(
            user_id=user_id,
            event="quiz_item_reviewed",
            properties={
                **analytics_props_common,
                "rating": rating,
                "fsrs_state_before": fsrs_state_before,
                "fsrs_state_after": progress.state,
                "reps": progress.reps,
                "lapses": progress.lapses,
                "time_spent_ms": time_spent_ms,
                "session_id": session_id,
            },
        )
    except Exception:
        logger.exception("analytics_track_failed for quiz_item_reviewed")

    # Slice 6.0 §6.2 + I1 — Postgres dual-write. Wrapper guarantees that an
    # analytics-write failure never blocks the user's review request (D-7).
    try:
        await analytics_event_service.write_quiz_review_event(
            QuizReviewEventCreate(
                user_id=user_id,
                quiz_item_id=quiz_item_id,
                lesson_id=lesson.id,
                deck_id=deck.id,
                rating=rating,
                fsrs_state_before=fsrs_state_before,
                fsrs_state_after=progress.state,
                reps=progress.reps,
                lapses=progress.lapses,
                time_spent_ms=time_spent_ms,
                session_id=session_id,
                plan=plan,
                persona=persona,
            ),
            db=db,
        )
    except Exception:
        logger.exception("quiz_review_event_dual_write_failed")

    return QuizReviewResponse(
        quiz_item_id=quiz_item_id,
        fsrs_state=progress.state,
        stability=progress.stability,
        difficulty=progress.difficulty_fsrs,
        due_date=progress.due_date,
        reps=progress.reps,
        lapses=progress.lapses,
        scheduled_days=progress.scheduled_days,
    )


def _resolve_plan(user: Optional[User]) -> Optional[str]:
    """Best-effort plan extraction for analytics — only inspects already-loaded
    attributes to avoid triggering async lazy-loads from the synchronous service
    body. Returns None when the subscription is not eagerly loaded (e.g. service
    tests that construct User directly without going through `get_current_user`).
    """
    if user is None:
        return None
    from sqlalchemy import inspect

    state = inspect(user)
    if "subscription" in state.unloaded:
        return None  # don't trigger lazy load
    sub = user.subscription
    if sub is None:
        return "free"
    if getattr(sub, "status", None) != "active":
        return "free"
    return getattr(sub, "plan", "free")


def _state_before(progress: QuizItemProgress, pre_review_card: FsrsCard) -> str:
    """Best-effort pre-review state label for analytics.

    The pre-review card was already mutated through `_scheduler.review_card`
    by the time this is called (py-fsrs v6 returns a NEW card object, but
    we built the fsrs_card from the ORM row before mutation). We recover
    the pre-review state from the FsrsCard built before the review applied.
    """
    if pre_review_card.state is None:
        return "new"
    return _FSRS_TO_STATE.get(pre_review_card.state, "new")


async def get_quiz_progress(
    user_id: str,
    db: AsyncSession,
) -> QuizProgressResponse:
    """Aggregate quiz-item study stats for the caller.

    Mirrors `study_service.get_progress` byte-for-byte modulo the table
    swap. Quiz_items the user has never touched are not in the counts —
    they appear as fresh-fill in the daily queue.
    """
    rows = (
        await db.execute(
            select(
                QuizItemProgress.state,
                sa_func.count(QuizItemProgress.id).label("cnt"),
                sa_func.coalesce(sa_func.sum(QuizItemProgress.reps), 0).label("reps"),
                sa_func.coalesce(sa_func.sum(QuizItemProgress.lapses), 0).label("lapses"),
            )
            .where(QuizItemProgress.user_id == user_id)
            .group_by(QuizItemProgress.state)
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

    return QuizProgressResponse(
        total_reviewed=total_reviewed,
        by_state=by_state,
        total_reps=total_reps,
        total_lapses=total_lapses,
    )
