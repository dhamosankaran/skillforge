"""State-aware home dashboard evaluator (P5-S18c, spec #40).

Evaluates a user's home-page state on a single backend call and returns a
priority-ordered list of active states plus the context used to render
their widgets. Cached in Redis for 60 seconds; mutation hooks (card review,
mission lifecycle, scan completion, plan change, persona update) call
``invalidate(user_id)`` to bust the per-user cache.

State catalog and predicates are defined in
``docs/specs/phase-5/40-home-dashboard-state-aware.md``.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.core.config import get_settings
from app.models.card_progress import CardProgress
from app.models.gamification import GamificationStats, UserBadge
from app.models.mission import Mission
from app.models.subscription import Subscription
from app.models.tracker import TrackerApplicationModel
from app.models.user import User
from app.schemas.home import HomeStateContext, HomeStateResponse, NextInterview

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60
CACHE_KEY_PREFIX = "home_state:"

# Priority order — index 0 = highest priority. See spec §4.
STATE_PRIORITY: tuple[str, ...] = (
    "mission_overdue",
    "streak_at_risk",
    "mission_active",
    "resume_stale",
    "inactive_returner",
    "first_session_done",
)

# Thresholds (spec §3)
STREAK_AT_RISK_HOURS = 18
STREAK_AT_RISK_MIN_STREAK = 3
RESUME_STALE_DAYS = 21
INACTIVE_WINDOW_MIN_DAYS = 7
INACTIVE_WINDOW_MAX_DAYS = 30
FIRST_SESSION_REPS_CAP = 3
FIRST_REVIEW_BADGE_ID = "first_review"


# ── Redis helpers ───────────────────────────────────────────────────────────


def _get_redis() -> Optional[redis.Redis]:
    """Return a Redis client, or None if unavailable.

    Mirrors the pattern in ``geo_pricing_service`` — graceful degradation
    when Redis is offline so tests and dev without a Redis container still
    work.
    """
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        logger.debug("Redis unavailable — home_state cache disabled")
        return None


def _cache_key(user_id: str) -> str:
    return f"{CACHE_KEY_PREFIX}{user_id}"


def _read_cache(user_id: str, r: Optional[redis.Redis]) -> Optional[HomeStateResponse]:
    if r is None:
        return None
    try:
        raw = r.get(_cache_key(user_id))
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return HomeStateResponse.model_validate(json.loads(raw))
    except Exception:
        return None


def _write_cache(
    user_id: str, response: HomeStateResponse, r: Optional[redis.Redis]
) -> None:
    if r is None:
        return
    try:
        r.setex(
            _cache_key(user_id),
            CACHE_TTL_SECONDS,
            response.model_dump_json(),
        )
    except Exception:
        logger.debug("home_state cache write failed for user_id=%s", user_id)


def invalidate(user_id: str, r: Optional[redis.Redis] = None) -> None:
    """Delete the cached home_state entry for one user.

    Fire-and-forget: failure is logged but never raised. Called from
    mutation sites enumerated in spec §6.
    """
    client = r if r is not None else _get_redis()
    if client is None:
        return
    try:
        client.delete(_cache_key(user_id))
    except Exception:
        logger.debug("home_state cache invalidate failed for user_id=%s", user_id)


# ── Per-state predicates ────────────────────────────────────────────────────


def _check_streak_at_risk(
    *, current_streak: int, last_review_at: Optional[datetime], now: datetime
) -> bool:
    if current_streak < STREAK_AT_RISK_MIN_STREAK:
        return False
    if last_review_at is None:
        return False
    return (now - last_review_at) > timedelta(hours=STREAK_AT_RISK_HOURS)


def _check_mission_active(
    *, mission_target_date: Optional[date], today: date
) -> bool:
    if mission_target_date is None:
        return False
    return mission_target_date >= today


def _check_mission_overdue(
    *, mission_target_date: Optional[date], today: date
) -> bool:
    if mission_target_date is None:
        return False
    return mission_target_date < today


def _check_resume_stale(
    *, last_scan_date: Optional[datetime], now: datetime
) -> bool:
    if last_scan_date is None:
        return False
    # Tracker.created_at is timezone-naive; compare against naive UTC now.
    naive_now = now.replace(tzinfo=None) if now.tzinfo is not None else now
    naive_scan = (
        last_scan_date.replace(tzinfo=None)
        if last_scan_date.tzinfo is not None
        else last_scan_date
    )
    return (naive_now - naive_scan) > timedelta(days=RESUME_STALE_DAYS)


def _check_inactive_returner(
    *,
    last_active_date: Optional[date],
    longest_streak: int,
    today: date,
) -> bool:
    if last_active_date is None:
        return False
    if longest_streak < 1:
        return False
    days_gone = (today - last_active_date).days
    return INACTIVE_WINDOW_MIN_DAYS <= days_gone <= INACTIVE_WINDOW_MAX_DAYS


def _check_first_session_done(
    *, has_first_review_badge: bool, total_reps: int
) -> bool:
    return has_first_review_badge and total_reps <= FIRST_SESSION_REPS_CAP


# ── Next-interview selection (spec #57 §2.2) ───────────────────────────────


async def get_next_interview(
    user_id: str, db: AsyncSession
) -> Optional[NextInterview]:
    """Return the user's nearest upcoming tracker-level interview, if any.

    Selection rule (spec #57 §2.2):
      MIN(interview_date)
        WHERE user_id = :user_id
          AND interview_date IS NOT NULL
          AND interview_date >= CURRENT_DATE
          AND status IN ('Applied', 'Interview')
      tie-break: earliest created_at wins.

    Returns ``None`` when no row matches.
    """
    today = date.today()
    stmt = (
        select(
            TrackerApplicationModel.id,
            TrackerApplicationModel.interview_date,
            TrackerApplicationModel.company,
        )
        .where(TrackerApplicationModel.user_id == user_id)
        .where(TrackerApplicationModel.interview_date.is_not(None))
        .where(TrackerApplicationModel.interview_date >= today)
        .where(TrackerApplicationModel.status.in_(["Applied", "Interview"]))
        .order_by(
            TrackerApplicationModel.interview_date.asc(),
            TrackerApplicationModel.created_at.asc(),
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    tracker_id, iv_date, company = row
    return NextInterview(date=iv_date, company=company, tracker_id=tracker_id)


# ── Compute (uncached) ──────────────────────────────────────────────────────


async def _load_context(
    user: User, db: AsyncSession
) -> tuple[HomeStateContext, dict[str, Any]]:
    """Load all data needed for state evaluation in one async block.

    Returns ``(context, raw)`` where ``raw`` carries the extra signals
    used by predicates but not exposed in the response (e.g. badge
    presence, total reps, longest_streak).
    """
    user_id = user.id

    raw: dict[str, Any] = {
        "longest_streak": 0,
        "has_first_review_badge": False,
        "total_reps": 0,
        "last_active_date": None,
    }

    context = HomeStateContext()

    # GamificationStats (current_streak, longest_streak, last_active_date)
    try:
        stats = (
            await db.execute(
                select(GamificationStats).where(
                    GamificationStats.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if stats is not None:
            context.current_streak = stats.current_streak
            raw["longest_streak"] = stats.longest_streak
            raw["last_active_date"] = stats.last_active_date
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "home_state: GamificationStats lookup failed for %s: %s",
            user_id,
            exc,
        )

    # last_review_at — MAX(CardProgress.last_reviewed)
    try:
        last_review = (
            await db.execute(
                select(func.max(CardProgress.last_reviewed)).where(
                    CardProgress.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        context.last_review_at = last_review
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "home_state: last_review aggregate failed for %s: %s",
            user_id,
            exc,
        )

    # Active mission (if any)
    try:
        mission = (
            await db.execute(
                select(Mission)
                .where(Mission.user_id == user_id)
                .where(Mission.status == "active")
            )
        ).scalar_one_or_none()
        if mission is not None:
            context.active_mission_id = mission.id
            context.mission_target_date = mission.target_date
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "home_state: active mission lookup failed for %s: %s",
            user_id,
            exc,
        )

    # next_interview — spec #57 §2.2 selection rule.
    try:
        context.next_interview = await get_next_interview(user_id, db)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "home_state: next_interview lookup failed for %s: %s",
            user_id,
            exc,
        )

    # last_scan_date — MAX(TrackerApplicationModel.created_at)
    try:
        last_scan = (
            await db.execute(
                select(func.max(TrackerApplicationModel.created_at)).where(
                    TrackerApplicationModel.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        context.last_scan_date = last_scan
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "home_state: last_scan aggregate failed for %s: %s",
            user_id,
            exc,
        )

    # Subscription plan
    try:
        sub = (
            await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
        ).scalar_one_or_none()
        if sub is not None:
            context.plan = sub.plan
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "home_state: subscription lookup failed for %s: %s",
            user_id,
            exc,
        )

    # First-review badge presence
    try:
        badge = (
            await db.execute(
                select(UserBadge.id)
                .where(UserBadge.user_id == user_id)
                .where(UserBadge.badge_id == FIRST_REVIEW_BADGE_ID)
                .limit(1)
            )
        ).scalar_one_or_none()
        raw["has_first_review_badge"] = badge is not None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "home_state: badge lookup failed for %s: %s", user_id, exc
        )

    # Total reps across all card_progress rows
    try:
        total_reps = (
            await db.execute(
                select(func.coalesce(func.sum(CardProgress.reps), 0)).where(
                    CardProgress.user_id == user_id
                )
            )
        ).scalar_one()
        raw["total_reps"] = int(total_reps or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "home_state: total reps aggregate failed for %s: %s",
            user_id,
            exc,
        )

    # last_activity_at = max(last_review_at, last_scan_date)
    candidates = [
        d for d in (context.last_review_at, context.last_scan_date) if d is not None
    ]
    if candidates:
        # Normalize to tz-aware so max() doesn't blow up on a mix.
        normalized = []
        for d in candidates:
            if d.tzinfo is None:
                normalized.append(d.replace(tzinfo=timezone.utc))
            else:
                normalized.append(d)
        context.last_activity_at = max(normalized)

    return context, raw


def _resolve_states(
    *, context: HomeStateContext, raw: dict[str, Any], now: datetime, today: date
) -> list[str]:
    """Apply per-state predicates and priority/exclusion rules. Returns
    the active states in priority order (highest first).
    """
    active: set[str] = set()

    # mission_active vs mission_overdue (mutually exclusive)
    if context.mission_target_date is not None:
        if _check_mission_overdue(
            mission_target_date=context.mission_target_date, today=today
        ):
            active.add("mission_overdue")
        elif _check_mission_active(
            mission_target_date=context.mission_target_date, today=today
        ):
            active.add("mission_active")

    if _check_streak_at_risk(
        current_streak=context.current_streak,
        last_review_at=context.last_review_at,
        now=now,
    ):
        active.add("streak_at_risk")

    if _check_resume_stale(
        last_scan_date=context.last_scan_date, now=now
    ):
        active.add("resume_stale")

    inactive = _check_inactive_returner(
        last_active_date=raw.get("last_active_date"),
        longest_streak=raw.get("longest_streak", 0),
        today=today,
    )
    first_session = _check_first_session_done(
        has_first_review_badge=raw.get("has_first_review_badge", False),
        total_reps=raw.get("total_reps", 0),
    )

    # inactive_returner ⊕ first_session_done — higher priority wins
    if inactive:
        active.add("inactive_returner")
    elif first_session:
        active.add("first_session_done")

    # Sort by priority order
    return [s for s in STATE_PRIORITY if s in active]


async def _compute_state_uncached(
    user: User, db: AsyncSession
) -> HomeStateResponse:
    now = datetime.now(timezone.utc)
    today = now.date()

    context, raw = await _load_context(user, db)
    states = _resolve_states(context=context, raw=raw, now=now, today=today)

    return HomeStateResponse(
        persona=user.persona,
        states=states,
        context=context,
    )


# ── Public API ──────────────────────────────────────────────────────────────


async def evaluate_state(
    user: User,
    db: AsyncSession,
    r: Optional[redis.Redis] = None,
) -> HomeStateResponse:
    """Return the priority-ordered active states plus context for the user.

    Reads Redis first; on miss, computes fresh and writes back. On any
    fatal failure during compute, returns an empty-states response with a
    best-effort context — frontend treats this identically to "no states
    active" per spec §5.
    """
    client = r if r is not None else _get_redis()

    cached = _read_cache(user.id, client)
    if cached is not None:
        analytics_track(
            user_id=user.id,
            event="home_state_evaluated",
            properties={
                "persona": cached.persona,
                "states": cached.states,
                "state_count": len(cached.states),
                "cache_hit": True,
            },
        )
        return cached

    try:
        response = await _compute_state_uncached(user, db)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "home_state evaluation failed for user_id=%s: %s", user.id, exc
        )
        analytics_track(
            user_id=user.id,
            event="home_state_evaluation_failed",
            properties={"error_code": exc.__class__.__name__},
        )
        return HomeStateResponse(persona=user.persona, states=[])

    _write_cache(user.id, response, client)

    analytics_track(
        user_id=user.id,
        event="home_state_evaluated",
        properties={
            "persona": response.persona,
            "states": response.states,
            "state_count": len(response.states),
            "cache_hit": False,
        },
    )

    return response
