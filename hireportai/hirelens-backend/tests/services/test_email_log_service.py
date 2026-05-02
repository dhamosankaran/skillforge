"""email_log_service tests — record_send + was_sent_today.

Spec: docs/specs/phase-6/13-pro-digest-opt-out.md §10.1 + AC-6..AC-8.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.email_log import EmailLog
from app.models.user import User
from app.services import email_log_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(db_session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@email-log.test",
        name="Email Log Tester",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_record_send_inserts_row(db_session) -> None:
    user = await _user(db_session)
    today = date(2026, 5, 1)

    row = await email_log_service.record_send(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        sent_date=today,
        resend_id="resend_abc",
    )
    assert row.id is not None
    assert row.user_id == user.id
    assert row.email_type == "pro_digest"
    assert row.sent_date == today
    assert row.resend_id == "resend_abc"

    fetched = (
        await db_session.execute(
            select(EmailLog).where(EmailLog.user_id == user.id)
        )
    ).scalars().all()
    assert len(fetched) == 1


async def test_record_send_handles_none_resend_id(db_session) -> None:
    user = await _user(db_session)
    row = await email_log_service.record_send(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        sent_date=date(2026, 5, 1),
        resend_id=None,
    )
    assert row.resend_id is None


async def test_record_send_duplicate_raises_integrity_error(db_session) -> None:
    user = await _user(db_session)
    today = date(2026, 5, 1)
    await email_log_service.record_send(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        sent_date=today,
    )
    with pytest.raises(IntegrityError):
        await email_log_service.record_send(
            db_session,
            user_id=user.id,
            email_type="pro_digest",
            sent_date=today,
        )


async def test_was_sent_today_false_when_no_row(db_session) -> None:
    user = await _user(db_session)
    assert await email_log_service.was_sent_today(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        today=date(2026, 5, 1),
    ) is False


async def test_was_sent_today_true_after_record(db_session) -> None:
    user = await _user(db_session)
    today = date(2026, 5, 1)
    await email_log_service.record_send(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        sent_date=today,
    )
    assert await email_log_service.was_sent_today(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        today=today,
    ) is True


async def test_was_sent_today_isolated_per_email_type(db_session) -> None:
    user = await _user(db_session)
    today = date(2026, 5, 1)
    await email_log_service.record_send(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        sent_date=today,
    )
    assert await email_log_service.was_sent_today(
        db_session,
        user_id=user.id,
        email_type="daily_reminder",
        today=today,
    ) is False


async def test_was_sent_today_isolated_per_date(db_session) -> None:
    user = await _user(db_session)
    today = date(2026, 5, 1)
    yesterday = today - timedelta(days=1)
    await email_log_service.record_send(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        sent_date=today,
    )
    assert await email_log_service.was_sent_today(
        db_session,
        user_id=user.id,
        email_type="pro_digest",
        today=yesterday,
    ) is False
