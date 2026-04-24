"""Usage tracking and plan limit enforcement."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User

# Plan limits: {plan: {feature: max_per_window}}
# Window semantics: monthly by default. `analyze` uses lifetime (spec #56 LD-3).
PLAN_LIMITS = {
    "free": {
        "analyze": 1,  # spec #56 LD-1 — 1 lifetime scan per free user
        "rewrite": 0,
        "cover_letter": 0,
        "interview_prep": 3,
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

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
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

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
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
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

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


async def get_analyze_usage(user_id: str, db: AsyncSession) -> dict:
    """Lifetime analyze-usage snapshot for the `/payments/usage` endpoint.

    Returns {plan, scans_used, scans_remaining, max_scans, is_admin} per
    spec #56 §4.3 (with `is_admin` per the 2026-04-23 impl-slice amendment).
    """
    plan, role = await _get_plan_and_role(user_id, db)
    is_admin = role == "admin"

    scans_used = await _count_usage(user_id, "analyze", db, window="lifetime")

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    max_scans = limits.get("analyze", 0)

    if is_admin or max_scans == -1:
        # Admin bypass OR unlimited plan → -1 sentinel for both fields.
        return {
            "plan": plan,
            "scans_used": scans_used,
            "scans_remaining": -1,
            "max_scans": -1,
            "is_admin": is_admin,
        }

    remaining = max(0, max_scans - scans_used)
    return {
        "plan": plan,
        "scans_used": scans_used,
        "scans_remaining": remaining,
        "max_scans": max_scans,
        "is_admin": is_admin,
    }
