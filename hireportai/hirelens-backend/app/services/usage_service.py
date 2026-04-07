"""Usage tracking and plan limit enforcement."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.usage_log import UsageLog

# Plan limits: {plan: {feature: max_per_month}}
PLAN_LIMITS = {
    "free": {
        "analyze": 3,
        "rewrite": 0,
        "cover_letter": 0,
        "interview_prep": 5,
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


async def log_usage(
    user_id: str,
    feature: str,
    tokens: int,
    db: AsyncSession,
) -> None:
    """Record a usage event."""
    log = UsageLog(user_id=user_id, feature_used=feature, tokens_consumed=tokens)
    db.add(log)


async def check_usage_limit(
    user_id: str,
    feature: str,
    db: AsyncSession,
) -> bool:
    """Check if the user is within their plan's usage limit for a feature.

    Returns True if the action is allowed, False if limit exceeded.
    """
    # Get user's plan
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    plan = sub.plan if sub else "free"

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    max_uses = limits.get(feature, 0)

    if max_uses == -1:
        return True  # unlimited
    if max_uses == 0:
        return False  # feature not available on this plan

    # Count usage this month
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(UsageLog.id))
        .where(UsageLog.user_id == user_id)
        .where(UsageLog.feature_used == feature)
        .where(UsageLog.created_at >= month_start)
    )
    count = result.scalar() or 0
    return count < max_uses


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
