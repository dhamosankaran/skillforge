"""Spec #42 — paywall_service unit tests.

Covers the two functions that ship in this slice:
- ``record_dismissal`` (LD-8 60s idempotency)
- ``should_show_paywall`` (Pro bypass, per-trigger grace)

Win-back eligibility + send are deferred; their tests will land in
the follow-up back-burner slice.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.paywall_dismissal import PaywallDismissal
from app.models.subscription import Subscription
from app.models.user import User
from app.services import paywall_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _make_user(
    db_session,
    *,
    plan: str = "free",
    status: str = "active",
    role: str = "user",
) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Paywall Service Test",
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    sub = Subscription(user_id=user.id, plan=plan, status=status)
    db_session.add(sub)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ── record_dismissal ────────────────────────────────────────────────────────


async def test_record_dismissal_inserts_row(db_session):
    user = await _make_user(db_session)
    result = await paywall_service.record_dismissal(
        db_session,
        user_id=user.id,
        trigger="daily_review",
        action_count=1,
    )
    assert result["logged"] is True
    assert result["dismissal_id"]
    assert result["dismissals_in_window"] == 1

    rows = (
        await db_session.execute(
            select(PaywallDismissal).where(PaywallDismissal.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action_count_at_dismissal == 1


async def test_record_dismissal_idempotent_within_60s(db_session):
    user = await _make_user(db_session)
    first = await paywall_service.record_dismissal(
        db_session, user_id=user.id, trigger="daily_review"
    )
    second = await paywall_service.record_dismissal(
        db_session, user_id=user.id, trigger="daily_review"
    )

    assert first["logged"] is True
    assert second["logged"] is False
    assert second["dismissal_id"] == first["dismissal_id"]
    assert second["dismissals_in_window"] == 1

    rows = (
        await db_session.execute(
            select(PaywallDismissal).where(PaywallDismissal.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 1


async def test_record_dismissal_distinct_after_60s(db_session):
    """Row older than 60s does not trigger dedup — a fresh row lands."""
    user = await _make_user(db_session)

    # Seed one dismissal backdated beyond the 60s window.
    stale = PaywallDismissal(
        user_id=user.id,
        trigger="daily_review",
        dismissed_at=datetime.now(timezone.utc) - timedelta(seconds=61),
    )
    db_session.add(stale)
    await db_session.flush()

    result = await paywall_service.record_dismissal(
        db_session, user_id=user.id, trigger="daily_review"
    )
    assert result["logged"] is True
    assert result["dismissal_id"] != stale.id
    assert result["dismissals_in_window"] == 2

    rows = (
        await db_session.execute(
            select(PaywallDismissal).where(PaywallDismissal.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 2


async def test_record_dismissal_per_trigger_isolation(db_session):
    """Dedup is scoped per-trigger — same user, different trigger → new row."""
    user = await _make_user(db_session)
    first = await paywall_service.record_dismissal(
        db_session, user_id=user.id, trigger="daily_review"
    )
    second = await paywall_service.record_dismissal(
        db_session, user_id=user.id, trigger="interview_limit"
    )
    assert first["logged"] is True
    assert second["logged"] is True
    assert first["dismissal_id"] != second["dismissal_id"]

    rows = (
        await db_session.execute(
            select(PaywallDismissal).where(PaywallDismissal.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 2


# ── should_show_paywall ─────────────────────────────────────────────────────


async def test_should_show_paywall_pro_user_returns_false(db_session):
    pro = await _make_user(db_session, plan="pro")
    result = await paywall_service.should_show_paywall(
        db_session, user=pro, trigger="daily_review"
    )
    assert result == {"show": False, "attempts_until_next": 0}


async def test_should_show_paywall_admin_returns_false_even_if_free(db_session):
    admin = await _make_user(db_session, plan="free", role="admin")
    result = await paywall_service.should_show_paywall(
        db_session, user=admin, trigger="daily_review"
    )
    assert result == {"show": False, "attempts_until_next": 0}


async def test_should_show_paywall_free_no_history_returns_true(db_session):
    free = await _make_user(db_session)
    result = await paywall_service.should_show_paywall(
        db_session, user=free, trigger="daily_review"
    )
    assert result == {"show": True, "attempts_until_next": 3}


async def test_should_show_paywall_free_within_grace_returns_false(db_session):
    free = await _make_user(db_session)
    await paywall_service.record_dismissal(
        db_session, user_id=free.id, trigger="daily_review"
    )

    for attempts, expected_remaining in [(0, 3), (1, 2), (2, 1)]:
        result = await paywall_service.should_show_paywall(
            db_session,
            user=free,
            trigger="daily_review",
            attempts_since_dismiss=attempts,
        )
        assert result == {
            "show": False,
            "attempts_until_next": expected_remaining,
        }


async def test_should_show_paywall_free_after_grace_returns_true(db_session):
    free = await _make_user(db_session)
    await paywall_service.record_dismissal(
        db_session, user_id=free.id, trigger="daily_review"
    )
    result = await paywall_service.should_show_paywall(
        db_session,
        user=free,
        trigger="daily_review",
        attempts_since_dismiss=3,
    )
    assert result == {"show": True, "attempts_until_next": 3}


async def test_should_show_paywall_per_trigger_isolation(db_session):
    """Dismissing trigger A does not silence trigger B (LD-2)."""
    free = await _make_user(db_session)
    await paywall_service.record_dismissal(
        db_session, user_id=free.id, trigger="daily_review"
    )

    a = await paywall_service.should_show_paywall(
        db_session, user=free, trigger="daily_review"
    )
    b = await paywall_service.should_show_paywall(
        db_session, user=free, trigger="interview_limit"
    )

    assert a["show"] is False
    assert b["show"] is True
