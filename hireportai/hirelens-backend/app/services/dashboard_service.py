"""User-self FSRS dashboard aggregator — Phase 6 slice 6.8.

Spec: docs/specs/phase-6/09-fsrs-dashboard.md §4 + §5 + §6 + §12
D-1..D-14.

Public API:
  - ``aggregate_user_dashboard(user, db, *, retention_window_days)``

Read-only aggregation across:
  - ``quiz_item_progress`` (cards-due, deck-mastery sections)
  - ``quiz_review_events`` (retention curve, recent-review-history)
  - ``email_preferences`` (D-6 user-local date bucketing)
  - ``gamification_service.get_stats`` (streak section reuse)

Reuses ``curriculum_visibility`` helpers (slice 6.6 D-6) so retired,
archived, persona-invisible, and premium-for-free decks never
surface in the response (D-10).

Zero migrations, zero new write paths, zero PostHog payload changes.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import QuizReviewEvent
from app.models.deck import Deck
from app.models.email_preference import EmailPreference
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.quiz_item_progress import QuizItemProgress
from app.models.user import User
from app.schemas.dashboard import (
    CardsDueByState,
    CardsDueSection,
    DailyRetentionPoint,
    DashboardResponse,
    DeckMastery,
    DeckMasterySection,
    RecentReview,
    RetentionSection,
    ReviewHistorySection,
    StreakSection,
)
from app.services import gamification_service
from app.services.curriculum_visibility import (
    _allowed_tiers_for_user,
    _resolve_plan,
    _visible_persona_set,
)

logger = logging.getLogger(__name__)


# ── Locked constants (per §12 D-7..D-9, D-14) ───────────────────────────────

DEFAULT_RETENTION_WINDOW_DAYS = 30  # D-7
DEFAULT_REVIEW_HISTORY_WINDOW_DAYS = 30  # D-9 (same as retention)
DEFAULT_MAX_RECENT_REVIEWS = 20  # D-9
MASTERY_REPS_THRESHOLD = 3  # D-8

# py-fsrs Rating enum (locked at slice 6.2 schema): Again=1, Hard=2,
# Good=3, Easy=4. D-5 locks recall = (3, 4); lapse = (1).
_RECALL_RATINGS = (3, 4)
_LAPSE_RATING = 1


# ── Public API ──────────────────────────────────────────────────────────────


async def aggregate_user_dashboard(
    user: User,
    db: AsyncSession,
    *,
    retention_window_days: int = DEFAULT_RETENTION_WINDOW_DAYS,
    review_history_window_days: int = DEFAULT_REVIEW_HISTORY_WINDOW_DAYS,
    max_recent_reviews: int = DEFAULT_MAX_RECENT_REVIEWS,
) -> DashboardResponse:
    """Return the full dashboard envelope for ``user``.

    Five private aggregators run sequentially against indexed reads
    (~200ms total per §6.4). Cold-start: when both the cards-due
    progress count AND the retention sample size are zero, the
    envelope flips ``is_cold_start=True``; section payloads still
    serialise (zeroed/empty) so the FE renders cold-start variants
    per D-13.
    """
    plan = _resolve_plan(user)
    user_tz = await _get_user_timezone(user.id, db)

    cards_due = await _aggregate_cards_due(user, db)
    retention = await _aggregate_retention_curve(
        user.id, db, window_days=retention_window_days, user_tz=user_tz
    )
    deck_mastery = await _aggregate_deck_mastery(user, db)
    streak = await _aggregate_streak(user.id, db)
    review_history = await _aggregate_review_history(
        user.id,
        db,
        window_days=review_history_window_days,
        max_recent_reviews=max_recent_reviews,
    )

    is_cold_start = (
        cards_due.total_quiz_items_in_progress == 0
        and retention.sample_size == 0
    )

    return DashboardResponse(
        user_id=user.id,
        persona=user.persona,
        plan=plan,
        is_cold_start=is_cold_start,
        retention_window_days=retention_window_days,
        generated_at=datetime.now(timezone.utc),
        cards_due=cards_due,
        retention=retention,
        deck_mastery=deck_mastery,
        streak=streak,
        review_history=review_history,
    )


# ── User timezone (D-6) ─────────────────────────────────────────────────────


async def _get_user_timezone(user_id: str, db: AsyncSession) -> ZoneInfo:
    """Read ``email_preferences.timezone`` for the user.

    The column is NOT NULL with default ``'UTC'`` (per D-008 — no
    NULL fallback branch). When no row exists yet (user predates
    Phase-2 email-prefs auto-creation), fall back to UTC. An invalid
    timezone string also falls back to UTC + a WARNING log.
    """
    pref = (
        await db.execute(
            select(EmailPreference.timezone).where(
                EmailPreference.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    tz_name = pref or "UTC"
    try:
        return ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 — narrow ZoneInfo errors aren't a public API
        logger.warning(
            "dashboard_service: invalid timezone %r for user %s — defaulting to UTC",
            tz_name,
            user_id,
        )
        return ZoneInfo("UTC")


# ── Cards-due aggregator (§5.2) ─────────────────────────────────────────────


async def _aggregate_cards_due(
    user: User, db: AsyncSession
) -> CardsDueSection:
    """Count `quiz_item_progress` rows by state + due-window.

    Visibility filter chain applied via JOIN to deck/lesson + the
    ``curriculum_visibility`` helpers — retired quiz_items, archived
    lessons / decks, persona-invisible decks, and premium-for-free
    decks do not count.
    """
    now = datetime.now(timezone.utc)
    next_week = now + timedelta(days=7)
    persona_set = _visible_persona_set(user)
    tier_set = _allowed_tiers_for_user(user)

    base_filters = [
        QuizItemProgress.user_id == user.id,
        QuizItem.retired_at.is_(None),
        Lesson.archived_at.is_(None),
        Lesson.published_at.is_not(None),
        Deck.archived_at.is_(None),
        Deck.persona_visibility.in_(persona_set),
        Deck.tier.in_(tier_set),
    ]

    base_join = (
        select(QuizItemProgress)
        .join(QuizItem, QuizItem.id == QuizItemProgress.quiz_item_id)
        .join(Lesson, Lesson.id == QuizItem.lesson_id)
        .join(Deck, Deck.id == Lesson.deck_id)
        .where(and_(*base_filters))
    )

    # Per-state COUNT
    state_rows = (
        await db.execute(
            select(QuizItemProgress.state, func.count())
            .select_from(QuizItemProgress)
            .join(QuizItem, QuizItem.id == QuizItemProgress.quiz_item_id)
            .join(Lesson, Lesson.id == QuizItem.lesson_id)
            .join(Deck, Deck.id == Lesson.deck_id)
            .where(and_(*base_filters))
            .group_by(QuizItemProgress.state)
        )
    ).all()
    state_counts = {state: count for state, count in state_rows}
    breakdown = CardsDueByState(
        new=state_counts.get("new", 0),
        learning=state_counts.get("learning", 0),
        review=state_counts.get("review", 0),
        relearning=state_counts.get("relearning", 0),
    )

    # Due-window counts: states learning/review/relearning use due_date;
    # state='new' is excluded from "due" semantics per slice 6.2 §6.1.
    due_active_states = ("learning", "review", "relearning")
    due_today = (
        await db.execute(
            select(func.count())
            .select_from(QuizItemProgress)
            .join(QuizItem, QuizItem.id == QuizItemProgress.quiz_item_id)
            .join(Lesson, Lesson.id == QuizItem.lesson_id)
            .join(Deck, Deck.id == Lesson.deck_id)
            .where(
                and_(
                    *base_filters,
                    QuizItemProgress.state.in_(due_active_states),
                    QuizItemProgress.due_date <= now,
                )
            )
        )
    ).scalar_one()
    due_next_7_days = (
        await db.execute(
            select(func.count())
            .select_from(QuizItemProgress)
            .join(QuizItem, QuizItem.id == QuizItemProgress.quiz_item_id)
            .join(Lesson, Lesson.id == QuizItem.lesson_id)
            .join(Deck, Deck.id == Lesson.deck_id)
            .where(
                and_(
                    *base_filters,
                    QuizItemProgress.state.in_(due_active_states),
                    QuizItemProgress.due_date <= next_week,
                )
            )
        )
    ).scalar_one()

    total = sum(state_counts.values())
    return CardsDueSection(
        due_today=due_today,
        due_next_7_days=due_next_7_days,
        due_breakdown_by_state=breakdown,
        total_quiz_items_in_progress=total,
    )


# ── Retention curve aggregator (§5.3, D-5 + D-6) ────────────────────────────


async def _aggregate_retention_curve(
    user_id: str,
    db: AsyncSession,
    *,
    window_days: int,
    user_tz: ZoneInfo,
) -> RetentionSection:
    """Aggregate `quiz_review_events` over the retention window.

    Ratings counted per D-5: recall = (3, 4) Good+Easy; lapse = (1)
    Again. Hard=(2) is excluded from both surfaces. Series is
    continuous — every date in [start, today] appears in
    ``daily_retention`` even with `sample_size=0`.

    Date bucketing per D-6: user-local via ``email_preferences.timezone``.
    """
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc - timedelta(days=window_days)

    rows = (
        await db.execute(
            select(QuizReviewEvent.rating, QuizReviewEvent.reviewed_at)
            .where(
                QuizReviewEvent.user_id == user_id,
                QuizReviewEvent.reviewed_at >= cutoff_utc,
            )
        )
    ).all()

    # Bucket per local date
    per_date: dict[date, list[int]] = {}
    for rating, reviewed_at in rows:
        local_date = reviewed_at.astimezone(user_tz).date()
        per_date.setdefault(local_date, []).append(rating)

    today_local = now_utc.astimezone(user_tz).date()
    start_local = today_local - timedelta(days=window_days - 1)

    daily: list[DailyRetentionPoint] = []
    cursor = start_local
    while cursor <= today_local:
        ratings = per_date.get(cursor, [])
        sample = len(ratings)
        if sample == 0:
            recall = None
        else:
            recalled = sum(1 for r in ratings if r in _RECALL_RATINGS)
            recall = recalled / sample
        daily.append(
            DailyRetentionPoint(
                date=cursor, sample_size=sample, recall_rate=recall
            )
        )
        cursor = cursor + timedelta(days=1)

    sample_size = len(rows)
    if sample_size == 0:
        recall_overall = 0.0
        lapse_overall = 0.0
    else:
        recalled_count = sum(1 for rating, _ in rows if rating in _RECALL_RATINGS)
        lapsed_count = sum(1 for rating, _ in rows if rating == _LAPSE_RATING)
        recall_overall = recalled_count / sample_size
        lapse_overall = lapsed_count / sample_size

    return RetentionSection(
        sample_size=sample_size,
        overall_recall_rate=recall_overall,
        overall_lapse_rate=lapse_overall,
        daily_retention=daily,
    )


# ── Deck mastery aggregator (§5.4, D-8 + D-10) ──────────────────────────────


async def _aggregate_deck_mastery(
    user: User, db: AsyncSession
) -> DeckMasterySection:
    """Per-deck mastery rollup over the visible deck set.

    `mastered` per D-8: ``state == 'review' AND reps >= MASTERY_REPS_THRESHOLD``.
    Visibility filter chain: ``curriculum_visibility`` helpers + the
    Phase-6 archived/published/retired/persona/tier chain. Sorted by
    ``mastery_pct DESC, display_order ASC``.

    Partial-failure tolerance per slice 6.6 D-16: a single deck's
    mastery query that errors gets skipped + WARNING-logged so the
    rest of the response still ships.
    """
    persona_set = _visible_persona_set(user)
    tier_set = _allowed_tiers_for_user(user)

    decks = (
        await db.execute(
            select(Deck)
            .where(
                Deck.archived_at.is_(None),
                Deck.persona_visibility.in_(persona_set),
                Deck.tier.in_(tier_set),
            )
            .order_by(Deck.display_order.asc())
        )
    ).scalars().all()

    out: list[DeckMastery] = []
    for deck in decks:
        try:
            row = await _aggregate_one_deck(user.id, deck, db)
            out.append(row)
        except SQLAlchemyError:  # pragma: no cover — defensive D-16
            logger.warning(
                "dashboard_service: deck mastery aggregation failed for "
                "deck %s; skipping",
                deck.id,
            )
            continue

    # mastery DESC, then display_order ASC (stable secondary order)
    out.sort(
        key=lambda d: (
            -d.mastery_pct,
            next((dk.display_order for dk in decks if dk.id == d.deck_id), 0),
        )
    )
    return DeckMasterySection(decks=out)


async def _aggregate_one_deck(
    user_id: str, deck: Deck, db: AsyncSession
) -> DeckMastery:
    """Compute one deck's mastery row.

    All COUNT subqueries respect the visibility filter chain at the
    quiz_item / lesson level — retired quiz_items + archived /
    unpublished lessons are excluded from `total_quiz_items_visible`.
    """
    base_qi = (
        select(QuizItem.id)
        .join(Lesson, Lesson.id == QuizItem.lesson_id)
        .where(
            Lesson.deck_id == deck.id,
            QuizItem.retired_at.is_(None),
            Lesson.archived_at.is_(None),
            Lesson.published_at.is_not(None),
        )
    )

    total_visible = (
        await db.execute(
            select(func.count()).select_from(base_qi.subquery())
        )
    ).scalar_one()

    visible_ids_subq = base_qi.subquery()

    with_progress = (
        await db.execute(
            select(func.count(QuizItemProgress.id))
            .where(
                QuizItemProgress.user_id == user_id,
                QuizItemProgress.quiz_item_id.in_(select(visible_ids_subq.c.id)),
            )
        )
    ).scalar_one()

    mastered = (
        await db.execute(
            select(func.count(QuizItemProgress.id))
            .where(
                QuizItemProgress.user_id == user_id,
                QuizItemProgress.quiz_item_id.in_(select(visible_ids_subq.c.id)),
                QuizItemProgress.state == "review",
                QuizItemProgress.reps >= MASTERY_REPS_THRESHOLD,
            )
        )
    ).scalar_one()

    pct = (mastered / total_visible) if total_visible > 0 else 0.0

    return DeckMastery(
        deck_id=deck.id,
        deck_slug=deck.slug,
        deck_title=deck.title,
        total_quiz_items_visible=total_visible,
        quiz_items_with_progress=with_progress,
        quiz_items_mastered=mastered,
        mastery_pct=pct,
    )


# ── Streak aggregator (§5.5) ────────────────────────────────────────────────


async def _aggregate_streak(
    user_id: str, db: AsyncSession
) -> StreakSection:
    """Reuse Phase-2 `gamification_service.get_stats` field-for-field.

    Re-deriving streak math here would duplicate Phase-2 logic and
    risk drift (per spec §6.3).
    """
    view = await gamification_service.get_stats(user_id=user_id, db=db)
    return StreakSection(
        current_streak=view.current_streak,
        longest_streak=view.longest_streak,
        last_active_date=view.last_active_date,
        freezes_available=view.freezes_available,
        total_xp=view.total_xp,
    )


# ── Review-history aggregator (§5.6, D-9) ───────────────────────────────────


async def _aggregate_review_history(
    user_id: str,
    db: AsyncSession,
    *,
    window_days: int,
    max_recent_reviews: int,
) -> ReviewHistorySection:
    """Newest-first reviews capped at ``max_recent_reviews`` per D-9.

    JOIN against `lessons` + `decks` for the row-display fields
    (`lesson_title`, `deck_slug`). Window matches retention by default
    per D-9 — review-history takes its own constant only if a future
    amendment splits them.
    """
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=window_days)

    total_in_window = (
        await db.execute(
            select(func.count())
            .select_from(QuizReviewEvent)
            .where(
                QuizReviewEvent.user_id == user_id,
                QuizReviewEvent.reviewed_at >= cutoff_utc,
            )
        )
    ).scalar_one()

    rows = (
        await db.execute(
            select(
                QuizReviewEvent.quiz_item_id,
                QuizReviewEvent.lesson_id,
                Lesson.title.label("lesson_title"),
                Deck.slug.label("deck_slug"),
                QuizReviewEvent.rating,
                QuizReviewEvent.fsrs_state_after,
                QuizReviewEvent.reviewed_at,
            )
            .join(Lesson, Lesson.id == QuizReviewEvent.lesson_id)
            .join(Deck, Deck.id == QuizReviewEvent.deck_id)
            .where(
                QuizReviewEvent.user_id == user_id,
                QuizReviewEvent.reviewed_at >= cutoff_utc,
            )
            .order_by(QuizReviewEvent.reviewed_at.desc())
            .limit(max_recent_reviews)
        )
    ).all()

    recent = [
        RecentReview(
            quiz_item_id=r.quiz_item_id,
            lesson_id=r.lesson_id,
            lesson_title=r.lesson_title,
            deck_slug=r.deck_slug,
            rating=r.rating,
            fsrs_state_after=r.fsrs_state_after,
            reviewed_at=r.reviewed_at,
        )
        for r in rows
    ]

    return ReviewHistorySection(
        window_days=window_days,
        total_in_window=total_in_window,
        recent_reviews=recent,
    )
