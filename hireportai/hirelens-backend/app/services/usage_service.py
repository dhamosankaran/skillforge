"""Usage tracking and plan limit enforcement."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User

# Plan limits: {plan: {feature: max_per_window}}
# Window semantics: monthly by default. `analyze` uses lifetime (spec #56 LD-3).
#
# Two free-tier cells are env-tunable for testing affordance —
# `analyze` (spec #56) and `interview_prep` (spec #49 §3.4) — sourced
# from Settings.free_lifetime_scan_limit / free_monthly_interview_limit.
# Defaults match production. Internal callers go through `_plan_limits(plan)`
# so monkeypatching `settings.free_*_limit` propagates without rebuilding
# this dict; PLAN_LIMITS is also seeded from the same Settings on import
# so direct importers (e.g. tests/test_payments_usage_route.py) see the
# active production values.
_settings = get_settings()
PLAN_LIMITS = {
    "free": {
        "analyze": _settings.free_lifetime_scan_limit,  # spec #56 LD-1
        "rewrite": 0,
        "cover_letter": 0,
        "interview_prep": _settings.free_monthly_interview_limit,
        "resume_optimize": 0,
    },
    "pro": {
        "analyze": -1,  # unlimited
        "rewrite": -1,
        "cover_letter": -1,
        "interview_prep": -1,
        "resume_optimize": 0,
    },
    "enterprise": {
        "analyze": -1,
        "rewrite": -1,
        "cover_letter": -1,
        "interview_prep": -1,
        "resume_optimize": -1,
    },
}
del _settings


def _plan_limits(plan: str) -> dict[str, int]:
    """Per-feature caps for `plan`, with the two env-tunable free cells
    re-read live from Settings so test monkeypatching of
    `settings.free_lifetime_scan_limit` / `free_monthly_interview_limit`
    propagates without rebuilding PLAN_LIMITS.
    """
    base = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    if plan != "free":
        return base
    s = get_settings()
    return {
        **base,
        "analyze": s.free_lifetime_scan_limit,
        "interview_prep": s.free_monthly_interview_limit,
    }


Window = Literal["monthly", "lifetime"]


async def log_usage(
    user_id: str,
    feature: str,
    tokens: int,
    db: AsyncSession,
) -> None:
    """Record a usage event."""
    log = UsageLog(user_id=user_id, feature_used=feature, tokens_consumed=tokens)
    db.add(log)


async def _get_plan_and_role(user_id: str, db: AsyncSession) -> tuple[str, str]:
    """Fetch the user's plan and role in a single round-trip.

    Returns (plan, role). plan defaults to "free" if no active subscription
    exists; role defaults to "user" if the user row is missing (should not
    happen in practice — the caller passes a user_id from get_current_user).
    """
    sub_row = (
        await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
    ).scalar_one_or_none()
    plan = sub_row.plan if sub_row else "free"

    user_row = (
        await db.execute(select(User.role).where(User.id == user_id))
    ).scalar_one_or_none()
    role = user_row or "user"
    return plan, role


async def _count_usage(
    user_id: str, feature: str, db: AsyncSession, window: Window
) -> int:
    """Count usage rows for (user, feature) per the given window.

    - monthly: rows created in the current calendar month (server UTC clock).
    - lifetime: all rows, ever (no date filter). Used by the `analyze`
      feature per spec #56 LD-3.
    """
    stmt = (
        select(func.count(UsageLog.id))
        .where(UsageLog.user_id == user_id)
        .where(UsageLog.feature_used == feature)
    )
    if window == "monthly":
        # Naive datetime to match the tz-naive `usage_logs.created_at` column.
        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        stmt = stmt.where(UsageLog.created_at >= month_start)
    result = await db.execute(stmt)
    return int(result.scalar() or 0)


async def check_usage_limit(
    user_id: str,
    feature: str,
    db: AsyncSession,
    *,
    window: Window = "monthly",
) -> bool:
    """Check if the user is within their plan's usage limit for a feature.

    Returns True if the action is allowed, False if limit exceeded. Admin
    role bypasses regardless of plan (spec #56 LD-1; mirrors
    paywall_service.py:168 house convention).
    """
    plan, role = await _get_plan_and_role(user_id, db)
    if role == "admin":
        return True

    limits = _plan_limits(plan)
    max_uses = limits.get(feature, 0)

    if max_uses == -1:
        return True
    if max_uses == 0:
        return False

    count = await _count_usage(user_id, feature, db, window)
    return count < max_uses


async def check_and_increment(
    user_id: str,
    feature: str,
    db: AsyncSession,
    *,
    window: Window = "monthly",
) -> dict:
    """Check usage limit and increment if allowed.

    Returns { allowed: bool, used: int, remaining: int, limit: int, plan: str }.
    Pro / Enterprise / Admin are always allowed without counter check.

    `window="lifetime"` is used by the `analyze` feature per spec #56 LD-3
    (1 lifetime scan per free user). All other features default to monthly.
    """
    plan, role = await _get_plan_and_role(user_id, db)

    # Admin bypass (spec #56 LD-1) — same idiom as paywall_service.py:168.
    if role == "admin":
        return {"allowed": True, "used": 0, "remaining": -1, "limit": -1, "plan": plan}

    limits = _plan_limits(plan)
    max_uses = limits.get(feature, 0)

    if max_uses == -1:
        return {"allowed": True, "used": 0, "remaining": -1, "limit": -1, "plan": plan}
    if max_uses == 0:
        return {"allowed": False, "used": 0, "remaining": 0, "limit": 0, "plan": plan}

    count = await _count_usage(user_id, feature, db, window)

    if count >= max_uses:
        return {
            "allowed": False,
            "used": count,
            "remaining": 0,
            "limit": max_uses,
            "plan": plan,
        }

    # Log the usage (row persists on request commit; rolls back on error).
    await log_usage(user_id, feature, 0, db)
    used_after = count + 1
    remaining = max_uses - used_after
    return {
        "allowed": True,
        "used": used_after,
        "remaining": remaining,
        "limit": max_uses,
        "plan": plan,
    }


async def get_usage_summary(user_id: str, db: AsyncSession) -> dict:
    """Get usage stats for the current month."""
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get plan
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    plan = sub.plan if sub else "free"
    limits = _plan_limits(plan)

    # Count usage per feature this month
    result = await db.execute(
        select(UsageLog.feature_used, func.count(UsageLog.id))
        .where(UsageLog.user_id == user_id)
        .where(UsageLog.created_at >= month_start)
        .group_by(UsageLog.feature_used)
    )
    usage_counts = {row[0]: row[1] for row in result.all()}

    # Total tokens this month
    result = await db.execute(
        select(func.sum(UsageLog.tokens_consumed))
        .where(UsageLog.user_id == user_id)
        .where(UsageLog.created_at >= month_start)
    )
    total_tokens = result.scalar() or 0

    return {
        "plan": plan,
        "period_start": month_start.isoformat(),
        "usage": {
            feature: {
                "used": usage_counts.get(feature, 0),
                "limit": limit if limit != -1 else "unlimited",
            }
            for feature, limit in limits.items()
        },
        "total_tokens_consumed": total_tokens,
    }


def _counter_triple(used: int, max_uses: int, is_admin: bool) -> tuple[int, int, int]:
    """Return (used, remaining, max) with -1 sentinel for admin / unlimited.

    Shared by every feature column in the `/payments/usage` response.
    `used` echoes the raw lifetime count even for Pro / admin so admin
    dashboards can read real consumption; `remaining` / `max` flip to the
    unlimited sentinel.
    """
    if is_admin or max_uses == -1:
        return used, -1, -1
    remaining = max(0, max_uses - used)
    return used, remaining, max_uses


async def get_usage_snapshot(user_id: str, db: AsyncSession) -> dict:
    """Lifetime usage snapshot for the `/payments/usage` endpoint.

    Returns the flat shape defined by spec #56 §4.3 (scan fields) as
    extended by spec #58 §5 for rewrite + cover-letter counters:

        {
          plan, is_admin,
          scans_used, scans_remaining, max_scans,
          rewrites_used, rewrites_remaining, rewrites_max,
          cover_letters_used, cover_letters_remaining, cover_letters_max,
        }

    `/rewrite/section` shares the `"rewrite"` bucket per spec #58 §4.1
    Option (a), so `rewrites_used` counts `feature_used='rewrite'` rows
    only — the section handler writes into that same feature column.

    All `*_max` / `*_remaining` fields use the `-1` unlimited sentinel
    for Pro / Enterprise / admin; `plan` stays the actual subscription
    plan (admin-on-free returns `plan='free'` + `is_admin=true`).
    """
    plan, role = await _get_plan_and_role(user_id, db)
    is_admin = role == "admin"
    limits = _plan_limits(plan)

    scans_used_raw = await _count_usage(user_id, "analyze", db, window="lifetime")
    rewrites_used_raw = await _count_usage(user_id, "rewrite", db, window="lifetime")
    cover_letters_used_raw = await _count_usage(
        user_id, "cover_letter", db, window="lifetime"
    )
    # interview_prep is monthly, not lifetime — see PLAN_LIMITS comment.
    interview_preps_used_raw = await _count_usage(
        user_id, "interview_prep", db, window="monthly"
    )

    scans_used, scans_remaining, max_scans = _counter_triple(
        scans_used_raw, limits.get("analyze", 0), is_admin
    )
    rewrites_used, rewrites_remaining, rewrites_max = _counter_triple(
        rewrites_used_raw, limits.get("rewrite", 0), is_admin
    )
    (
        cover_letters_used,
        cover_letters_remaining,
        cover_letters_max,
    ) = _counter_triple(
        cover_letters_used_raw, limits.get("cover_letter", 0), is_admin
    )
    (
        interview_preps_used,
        interview_preps_remaining,
        interview_preps_max,
    ) = _counter_triple(
        interview_preps_used_raw, limits.get("interview_prep", 0), is_admin
    )

    return {
        "plan": plan,
        "is_admin": is_admin,
        # spec #56 — scans
        "scans_used": scans_used,
        "scans_remaining": scans_remaining,
        "max_scans": max_scans,
        # spec #58 — rewrites (shared bucket: /rewrite + /rewrite/section)
        "rewrites_used": rewrites_used,
        "rewrites_remaining": rewrites_remaining,
        "rewrites_max": rewrites_max,
        # spec #58 — cover letters (separate bucket)
        "cover_letters_used": cover_letters_used,
        "cover_letters_remaining": cover_letters_remaining,
        "cover_letters_max": cover_letters_max,
        # spec #49 §3.4 — interview_prep monthly cap; FE pre-flight gates the
        # Generate button on `interview_preps_used >= interview_preps_max`.
        "interview_preps_used": interview_preps_used,
        "interview_preps_remaining": interview_preps_remaining,
        "interview_preps_max": interview_preps_max,
    }


# Back-compat alias — some older callers (and tests) import the pre-spec-#58
# name. Kept so existing imports do not break; new callers should use
# `get_usage_snapshot` directly.
get_analyze_usage = get_usage_snapshot
