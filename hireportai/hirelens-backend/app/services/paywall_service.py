"""Paywall dismissal service — spec #42.

Two responsibilities:

1. ``record_dismissal`` — append a paywall_dismissals row, with LD-8 60s
   idempotency per (user_id, trigger).
2. ``should_show_paywall`` — answer whether the frontend should render the
   modal (vs. the silent inline nudge) for a given (user, trigger). Uses
   Strategy A from spec §5.3: frontend passes ``attempts_since_dismiss``
   as a query param; backend is stateless.

Win-back eligibility + win-back email send are deferred (see BACKLOG row
5.32 / the back-burner row created by this slice). ``users.downgraded_at``
is written by the ``customer.subscription.deleted`` webhook but not read
by anything in this slice.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paywall_dismissal import PaywallDismissal
from app.models.user import User

logger = logging.getLogger(__name__)


GRACE_ATTEMPTS = 3
IDEMPOTENCY_WINDOW_SECONDS = 60


class RecordDismissalResult(TypedDict):
    logged: bool
    dismissal_id: str
    dismissals_in_window: int


class ShouldShowPaywallResult(TypedDict):
    show: bool
    attempts_until_next: int


def _is_free(user: User) -> bool:
    """True when the user is on the free plan or has no active subscription.

    Mirrors the duplicated helper in ``app/api/v1/routes/study.py:34`` and
    ``app/services/card_service.py:35``. Pro + Enterprise + admin semantics
    are layered on top in the individual handlers (admin is role-gated, not
    plan-gated).
    """
    sub = getattr(user, "subscription", None)
    if sub is None:
        return True
    if sub.status != "active":
        return True
    return sub.plan == "free"


async def record_dismissal(
    db: AsyncSession,
    *,
    user_id: str,
    trigger: str,
    action_count: int | None = None,
) -> RecordDismissalResult:
    """Log a dismissal with 60s idempotency per (user_id, trigger).

    If a row for the same (user_id, trigger) was inserted within the last
    60 seconds (server UTC clock), returns that row's id without inserting
    a new one (LD-8). Otherwise inserts a fresh row.

    ``dismissals_in_window`` is the rolling 30-day count for
    (user_id, trigger), INCLUDING the just-logged (or echoed) row. Used by
    the dismissal endpoint for its response payload, and by the deferred
    win-back consumer once it lands.
    """
    now = datetime.now(timezone.utc)
    dedup_cutoff = now - timedelta(seconds=IDEMPOTENCY_WINDOW_SECONDS)

    recent = (
        await db.execute(
            select(PaywallDismissal)
            .where(
                PaywallDismissal.user_id == user_id,
                PaywallDismissal.trigger == trigger,
                PaywallDismissal.dismissed_at >= dedup_cutoff,
            )
            .order_by(PaywallDismissal.dismissed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if recent is not None:
        dismissals_in_window = await _count_in_30d(db, user_id, trigger)
        return RecordDismissalResult(
            logged=False,
            dismissal_id=recent.id,
            dismissals_in_window=dismissals_in_window,
        )

    row = PaywallDismissal(
        user_id=user_id,
        trigger=trigger,
        action_count_at_dismissal=action_count,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)

    dismissals_in_window = await _count_in_30d(db, user_id, trigger)
    return RecordDismissalResult(
        logged=True,
        dismissal_id=row.id,
        dismissals_in_window=dismissals_in_window,
    )


async def _count_in_30d(db: AsyncSession, user_id: str, trigger: str) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    count = (
        await db.execute(
            select(func.count(PaywallDismissal.id))
            .where(
                PaywallDismissal.user_id == user_id,
                PaywallDismissal.trigger == trigger,
                PaywallDismissal.dismissed_at >= cutoff,
            )
        )
    ).scalar_one()
    return int(count or 0)


async def should_show_paywall(
    db: AsyncSession,
    *,
    user: User,
    trigger: str,
    attempts_since_dismiss: int = 0,
) -> ShouldShowPaywallResult:
    """Compute modal-vs-inline-nudge for this (user, trigger).

    Rules (spec §7 AC-1..AC-4, LD-2, LD-7):

    - Pro / Enterprise / admin → never see paywall. Return
      ``{show: False, attempts_until_next: 0}``. The frontend short-
      circuits before calling this endpoint for those cohorts, but the
      backend defends the contract either way.
    - Free user with no prior dismissal for this trigger → modal shows.
    - Free user with a prior dismissal AND ``attempts_since_dismiss < 3``
      → silent inline nudge (``show: False``). ``attempts_until_next``
      decrements toward zero so the FE can render a countdown if it
      wants.
    - Free user with a prior dismissal AND
      ``attempts_since_dismiss >= 3`` → grace exhausted; modal shows
      again.

    Strategy A (spec §5.3): the 3-attempt grace counter lives in FE
    React state and is passed in via query param. Backend stays
    stateless — a refresh resets the grace. Accepted UX tradeoff for
    LD-3's intuition-based thresholds; revisit if production telemetry
    shows users exploiting the refresh.
    """
    # Admins and non-free plans bypass the wall entirely.
    if getattr(user, "role", "user") == "admin" or not _is_free(user):
        return ShouldShowPaywallResult(show=False, attempts_until_next=0)

    # Hard-wall carve-outs (amend spec #42 LD-1). Triggers listed below bypass
    # the 3-attempt grace for free users — every attempt re-opens the modal
    # regardless of `paywall_dismissals` history. Dismissal rows are still
    # logged (win-back telemetry / E-031); only the silencing is skipped.
    #   - `scan_limit`        — spec #56 LD-4 (1 lifetime ATS scan for free).
    #   - `rewrite_limit`     — spec #58 LD-5 (Pro-only; /rewrite +
    #                           /rewrite/section share the `"rewrite"` bucket
    #                           per spec #58 §4.1 Option a).
    #   - `cover_letter_limit`— spec #58 LD-5 (Pro-only; separate bucket).
    if trigger in {"scan_limit", "rewrite_limit", "cover_letter_limit"}:
        return ShouldShowPaywallResult(show=True, attempts_until_next=0)

    last = (
        await db.execute(
            select(PaywallDismissal.dismissed_at)
            .where(
                PaywallDismissal.user_id == user.id,
                PaywallDismissal.trigger == trigger,
            )
            .order_by(PaywallDismissal.dismissed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if last is None:
        # Never dismissed this trigger → modal shows.
        return ShouldShowPaywallResult(
            show=True, attempts_until_next=GRACE_ATTEMPTS
        )

    if attempts_since_dismiss >= GRACE_ATTEMPTS:
        return ShouldShowPaywallResult(
            show=True, attempts_until_next=GRACE_ATTEMPTS
        )

    remaining = max(0, GRACE_ATTEMPTS - attempts_since_dismiss)
    return ShouldShowPaywallResult(show=False, attempts_until_next=remaining)
