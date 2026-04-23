"""Admin analytics aggregations (spec #38 E-018b slice 2/4).

Two public entry points:

- ``get_metrics_summary(db, to_date)`` — six PRD §1.4 OKRs with 7d/30d
  deltas (spec AC-2). Pure Postgres.
- ``get_performance_summary(db, to_date)`` — operational snapshot (spec
  AC-3). LLM spend + Stripe webhook success in this slice; api_latency
  and error_rate are deferred (see schema docstring).

Both wrap in a Redis cache keyed by ``(endpoint, to_iso)`` with a 5-minute
TTL per spec §Caching. Graceful degradation on Redis outage mirrors
``home_state_service._get_redis``.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import redis
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.llm_router import TIER_PRICE_USD_PER_1M_TOKENS
from app.models.card_progress import CardProgress
from app.models.gamification import GamificationStats
from app.models.payment import Payment
from app.models.stripe_event import StripeEvent
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.admin_analytics import (
    MetricsResponse,
    MetricValue,
    PerformanceResponse,
)

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300
CACHE_KEY_PREFIX = "admin_analytics:"

# Feature → tier mapping for LLM spend attribution. Kept minimal — only
# features where ``usage_logs`` actually receives non-zero ``tokens_consumed``
# today (resume_optimize is the only live one; the rest are filed for when
# token metering lands across callers). Anything unmapped falls back to
# `fast` as the cheaper / more conservative estimate.
_FEATURE_TIER: dict[str, str] = {
    "resume_optimize": "reasoning",
    "rewrite": "reasoning",
    "cover_letter": "reasoning",
    "interview_prep": "reasoning",
    "analyze": "fast",
}


# ── Redis helpers ───────────────────────────────────────────────────────────

def _get_redis() -> Optional[redis.Redis]:
    """Best-effort Redis client; returns None when offline (mirrors home_state_service)."""
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        logger.debug("Redis unavailable — admin_analytics cache disabled")
        return None


def _cache_key(endpoint: str, to_iso: str) -> str:
    return f"{CACHE_KEY_PREFIX}{endpoint}:{to_iso}"


def _read_cache(key: str, r: Optional[redis.Redis]) -> Optional[dict]:
    if r is None:
        return None
    try:
        raw = r.get(key)
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _write_cache(key: str, payload: dict, r: Optional[redis.Redis]) -> None:
    if r is None:
        return
    try:
        r.setex(key, CACHE_TTL_SECONDS, json.dumps(payload, default=str))
    except Exception:
        logger.debug("Redis SETEX failed for %s; dropping write", key)


# ── Delta helper ────────────────────────────────────────────────────────────

def _pct_delta(current: float, past: float) -> float:
    """Return ((current - past) / past) * 100. 0.0 (not inf) when past == 0."""
    if past == 0:
        return 0.0
    return ((current - past) / past) * 100.0


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(dt: datetime) -> datetime:
    """Strip tzinfo for comparisons against tz-naive columns.

    User/Subscription/Payment/UsageLog/StripeEvent.created_at are all
    declared as `DateTime` (no tz) in the models, so asyncpg rejects
    tz-aware bindings. CardProgress.last_reviewed and
    GamificationStats.created_at are tz-aware — those keep the original dt.
    """
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


# ── Metrics (AC-2) ──────────────────────────────────────────────────────────

async def _registered_users_at(db: AsyncSession, moment: datetime) -> int:
    result = await db.execute(
        select(func.count(User.id)).where(User.created_at <= _naive_utc(moment))
    )
    return int(result.scalar() or 0)


async def _paying_pro_users_at(db: AsyncSession, moment: datetime) -> int:
    """Count pro subscriptions active at a given moment.

    Approximation: we treat `subscriptions.created_at <= moment` AND current
    `plan='pro'` AND `status='active'` as "pro at `moment`". This slightly
    over-counts historical pro users (a user who downgraded after `moment`
    still shows up as pro at `moment`) but is the cheapest read today.
    When churn history lands as a column it becomes exact.
    """
    result = await db.execute(
        select(func.count(Subscription.id))
        .where(Subscription.created_at <= _naive_utc(moment))
        .where(Subscription.plan == "pro")
        .where(Subscription.status == "active")
    )
    return int(result.scalar() or 0)


async def _dau_mau_at(db: AsyncSession, moment: datetime) -> float:
    """DAU / MAU ratio at a given moment. Source: CardProgress.last_reviewed.

    DAU = distinct users with any review in the 24h ending at `moment`.
    MAU = distinct users with any review in the 30d ending at `moment`.
    Returns 0.0 when MAU is 0. `last_reviewed` is a tz-aware column so we
    keep the tz-aware bound here (unlike the tz-naive `created_at` columns).
    """
    # Ensure tz-aware bound for tz-aware column.
    aware = moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)
    dau_result = await db.execute(
        select(func.count(func.distinct(CardProgress.user_id)))
        .where(CardProgress.last_reviewed >= aware - timedelta(days=1))
        .where(CardProgress.last_reviewed <= aware)
    )
    mau_result = await db.execute(
        select(func.count(func.distinct(CardProgress.user_id)))
        .where(CardProgress.last_reviewed >= aware - timedelta(days=30))
        .where(CardProgress.last_reviewed <= aware)
    )
    dau = int(dau_result.scalar() or 0)
    mau = int(mau_result.scalar() or 0)
    return (dau / mau) if mau > 0 else 0.0


async def _avg_streak_at(db: AsyncSession, moment: datetime) -> float:
    """Average current_streak across users whose stats row existed at `moment`.

    Filter is `gamification_stats.created_at <= moment`; we do NOT
    time-travel `current_streak` itself (the column has no history). So this
    is "avg current_streak today across users who had stats by `moment`" —
    fine for recent windows (1-30d); stale for old historical points.
    """
    # GamificationStats.created_at is tz-aware; keep tz-aware bound.
    aware = moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)
    result = await db.execute(
        select(func.avg(GamificationStats.current_streak))
        .where(GamificationStats.created_at <= aware)
        .where(GamificationStats.current_streak > 0)
    )
    avg = result.scalar()
    return float(avg or 0.0)


async def _ats_to_pro_conversion_in_window(
    db: AsyncSession, window_end: datetime, window_days: int = 30
) -> float:
    """Successful Stripe payments / distinct users who ran ATS analyze.

    Source caveat: ``usage_logs`` only logs ``analyze`` for free-tier users
    (Pro/Enterprise short-circuit before ``log_usage``), so the denominator
    is skewed low. The ratio is a free-tier conversion proxy, not a true
    product-wide funnel. Acknowledged in the schema docstring.
    """
    naive_end = _naive_utc(window_end)
    naive_start = naive_end - timedelta(days=window_days)
    scanned_result = await db.execute(
        select(func.count(func.distinct(UsageLog.user_id)))
        .where(UsageLog.feature_used == "analyze")
        .where(UsageLog.created_at >= naive_start)
        .where(UsageLog.created_at <= naive_end)
    )
    scanned = int(scanned_result.scalar() or 0)

    paid_result = await db.execute(
        select(func.count(func.distinct(Payment.user_id)))
        .where(Payment.status == "succeeded")
        .where(Payment.created_at >= naive_start)
        .where(Payment.created_at <= naive_end)
    )
    paid = int(paid_result.scalar() or 0)
    return (paid / scanned) if scanned > 0 else 0.0


async def _monthly_churn_at(
    db: AsyncSession, window_end: datetime, window_days: int = 30
) -> float:
    """(subs cancelled in window / subs active at window start) — see spec AC-2.

    "Cancelled in window" is approximated by ``status='canceled'`` with
    ``updated_at`` inside the window (the cancellation webhook bumps
    updated_at). "Active at window start" = subs with ``created_at <=
    window_start`` AND (``status='active'`` OR ``updated_at >= window_start``
    when currently cancelled). Returns 0.0 when the denominator is 0.
    """
    naive_end = _naive_utc(window_end)
    naive_start = naive_end - timedelta(days=window_days)

    canceled_result = await db.execute(
        select(func.count(Subscription.id))
        .where(Subscription.status == "canceled")
        .where(Subscription.updated_at >= naive_start)
        .where(Subscription.updated_at <= naive_end)
    )
    canceled = int(canceled_result.scalar() or 0)

    active_at_start_result = await db.execute(
        select(func.count(Subscription.id)).where(
            and_(
                Subscription.created_at <= naive_start,
                # Either still active today (never cancelled) or cancelled
                # after window_start (was active AT window_start).
                case(
                    (Subscription.status == "active", True),
                    (Subscription.updated_at >= naive_start, True),
                    else_=False,
                ),
            )
        )
    )
    active_at_start = int(active_at_start_result.scalar() or 0)
    return (canceled / active_at_start) if active_at_start > 0 else 0.0


async def _build_metric_value(
    db: AsyncSession,
    *,
    current_moment: datetime,
    d7_moment: datetime,
    d30_moment: datetime,
    fetch,
) -> MetricValue:
    current = float(await fetch(db, current_moment))
    d7 = float(await fetch(db, d7_moment))
    d30 = float(await fetch(db, d30_moment))
    return MetricValue(
        current=current,
        d7_ago=d7,
        d30_ago=d30,
        delta_7d_pct=_pct_delta(current, d7),
        delta_30d_pct=_pct_delta(current, d30),
    )


async def get_metrics_summary(
    db: AsyncSession, to_date: Optional[datetime] = None
) -> MetricsResponse:
    """Compute the six OKRs + deltas. Redis-cached 5 minutes."""
    to_date = to_date or _now_utc()
    to_iso = to_date.date().isoformat()

    r = _get_redis()
    cache_key = _cache_key("metrics", to_iso)
    cached = _read_cache(cache_key, r)
    if cached is not None:
        cached["from_cache"] = True
        return MetricsResponse.model_validate(cached)

    d7 = to_date - timedelta(days=7)
    d30 = to_date - timedelta(days=30)

    registered = await _build_metric_value(
        db,
        current_moment=to_date,
        d7_moment=d7,
        d30_moment=d30,
        fetch=_registered_users_at,
    )
    paying = await _build_metric_value(
        db,
        current_moment=to_date,
        d7_moment=d7,
        d30_moment=d30,
        fetch=_paying_pro_users_at,
    )
    dau_mau = await _build_metric_value(
        db,
        current_moment=to_date,
        d7_moment=d7,
        d30_moment=d30,
        fetch=_dau_mau_at,
    )
    streak = await _build_metric_value(
        db,
        current_moment=to_date,
        d7_moment=d7,
        d30_moment=d30,
        fetch=_avg_streak_at,
    )
    # Conversion + churn are window-based, not point-in-time, so we feed the
    # 30d window ending at each moment via a one-off wrapper.
    async def _conv_at(db, moment):
        return await _ats_to_pro_conversion_in_window(db, moment, 30)

    async def _churn_at(db, moment):
        return await _monthly_churn_at(db, moment, 30)

    conversion = await _build_metric_value(
        db,
        current_moment=to_date,
        d7_moment=d7,
        d30_moment=d30,
        fetch=_conv_at,
    )
    churn = await _build_metric_value(
        db,
        current_moment=to_date,
        d7_moment=d7,
        d30_moment=d30,
        fetch=_churn_at,
    )

    response = MetricsResponse(
        registered_users=registered,
        paying_pro_users=paying,
        dau_mau_ratio=dau_mau,
        avg_streak_length=streak,
        ats_to_pro_conversion=conversion,
        monthly_churn=churn,
        generated_at=_now_utc(),
        from_cache=False,
    )
    _write_cache(cache_key, response.model_dump(mode="json"), r)
    return response


# ── Performance (AC-3) ──────────────────────────────────────────────────────

async def _llm_spend_mtd(
    db: AsyncSession, window_end: datetime
) -> tuple[float, dict[str, float]]:
    """Month-to-date LLM spend: total + per-feature breakdown.

    Sum ``usage_logs.tokens_consumed`` grouped by ``feature_used`` within
    [month_start, window_end]. Convert via ``_FEATURE_TIER`` → tier →
    ``TIER_PRICE_USD_PER_1M_TOKENS``. Unmapped features are charged at the
    `fast` rate.
    """
    naive_end = _naive_utc(window_end)
    month_start = naive_end.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    result = await db.execute(
        select(
            UsageLog.feature_used,
            func.coalesce(func.sum(UsageLog.tokens_consumed), 0),
        )
        .where(UsageLog.created_at >= month_start)
        .where(UsageLog.created_at <= naive_end)
        .group_by(UsageLog.feature_used)
    )
    breakdown: dict[str, float] = {}
    total = 0.0
    for feature, tokens in result.all():
        tier = _FEATURE_TIER.get(feature, "fast")
        price = TIER_PRICE_USD_PER_1M_TOKENS.get(tier, 0.0)
        usd = (int(tokens or 0) / 1_000_000.0) * price
        breakdown[feature] = round(usd, 4)
        total += usd
    return round(total, 4), breakdown


async def _stripe_webhook_success_24h(
    db: AsyncSession, window_end: datetime
) -> tuple[Optional[float], bool]:
    """Stripe webhook success rate over 24h.

    `stripe_events` currently only stores processed (successful) events —
    no failure counter exists. If any row landed in the 24h window we
    report 100.0 with `available=True` (an honest statement about what we
    observed); if zero rows landed we return (None, False) so the tile
    renders "Coming soon / no data" rather than a misleading 100%. A
    failure-counter column (or a sibling `stripe_webhook_failure` log) is
    required to compute a real ratio; tracked under E-018b-follow-errors.
    """
    naive_end = _naive_utc(window_end)
    window_start = naive_end - timedelta(hours=24)
    result = await db.execute(
        select(func.count(StripeEvent.id))
        .where(StripeEvent.created_at >= window_start)
        .where(StripeEvent.created_at <= naive_end)
    )
    count = int(result.scalar() or 0)
    if count == 0:
        return None, False
    return 100.0, True


async def get_performance_summary(
    db: AsyncSession, to_date: Optional[datetime] = None
) -> PerformanceResponse:
    """Operational snapshot. Redis-cached 5 minutes.

    Shipped this slice: LLM spend (total + per-feature breakdown), Stripe
    webhook success. Deferred: `api_latency` (empty list + marker=False),
    `error_rate_24h_pct` (None + marker=False).
    """
    to_date = to_date or _now_utc()
    to_iso = to_date.date().isoformat()

    r = _get_redis()
    cache_key = _cache_key("performance", to_iso)
    cached = _read_cache(cache_key, r)
    if cached is not None:
        cached["from_cache"] = True
        return PerformanceResponse.model_validate(cached)

    spend_total, spend_breakdown = await _llm_spend_mtd(db, to_date)
    stripe_pct, stripe_available = await _stripe_webhook_success_24h(db, to_date)

    response = PerformanceResponse(
        llm_spend_estimate_usd=spend_total,
        llm_spend_breakdown=spend_breakdown,
        api_latency=[],
        api_latency_available=False,
        error_rate_24h_pct=None,
        error_rate_available=False,
        stripe_webhook_success_24h_pct=stripe_pct,
        stripe_webhook_available=stripe_available,
        generated_at=_now_utc(),
        from_cache=False,
    )
    _write_cache(cache_key, response.model_dump(mode="json"), r)
    return response
