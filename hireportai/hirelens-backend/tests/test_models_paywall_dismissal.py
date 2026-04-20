"""Spec #42 — paywall_dismissals model + user.downgraded_at column."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.paywall_dismissal import PaywallDismissal
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_paywall_dismissal_creation(db_session):
    """Row round-trips with server-default dismissed_at + nullable action count."""
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Dismiss Test",
    )
    db_session.add(user)
    await db_session.flush()

    dismissal = PaywallDismissal(
        user_id=user.id,
        trigger="daily_review",
        action_count_at_dismissal=1,
    )
    db_session.add(dismissal)
    await db_session.flush()
    await db_session.refresh(dismissal)

    assert dismissal.id is not None
    assert dismissal.user_id == user.id
    assert dismissal.trigger == "daily_review"
    assert dismissal.dismissed_at is not None
    assert dismissal.action_count_at_dismissal == 1

    # action_count nullable — second row without it
    dismissal2 = PaywallDismissal(user_id=user.id, trigger="daily_review")
    db_session.add(dismissal2)
    await db_session.flush()
    await db_session.refresh(dismissal2)
    assert dismissal2.action_count_at_dismissal is None


async def test_cascade_delete_on_user_removal(db_session):
    """ON DELETE CASCADE: removing the user removes their dismissals."""
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Cascade Test",
    )
    db_session.add(user)
    await db_session.flush()

    for trig in ("daily_review", "interview_limit", "daily_review"):
        db_session.add(PaywallDismissal(user_id=user.id, trigger=trig))
    await db_session.flush()

    rows = (
        await db_session.execute(
            select(PaywallDismissal).where(PaywallDismissal.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 3

    await db_session.delete(user)
    await db_session.flush()

    remaining = (
        await db_session.execute(
            select(PaywallDismissal).where(PaywallDismissal.user_id == user.id)
        )
    ).scalars().all()
    assert remaining == []


async def test_user_downgraded_at_defaults_null(db_session):
    """Fresh users land with downgraded_at = NULL — no churn timestamp yet."""
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Downgrade Default Test",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert user.downgraded_at is None
