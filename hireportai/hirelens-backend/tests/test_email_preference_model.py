"""EmailPreference model tests for the slice 6.13 additive column.

Spec: docs/specs/phase-6/13-pro-digest-opt-out.md §10.1 + AC-13.

Covers the on-disk shape — ``daily_digest_opt_out`` defaults False on
new rows and on existing rows the create_all path applies the same
default (mirrors prod alembic ``server_default=text("false")``).
"""
from __future__ import annotations

import secrets
import uuid

import pytest
from sqlalchemy import select

from app.models.email_preference import EmailPreference
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(db_session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@email-pref-model.test",
        name="Pref Model Tester",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_daily_digest_opt_out_defaults_false(db_session) -> None:
    user = await _user(db_session)
    pref = EmailPreference(
        user_id=user.id,
        daily_reminder=True,
        timezone="UTC",
        unsubscribe_token=secrets.token_hex(32),
    )
    db_session.add(pref)
    await db_session.flush()

    fetched = (
        await db_session.execute(
            select(EmailPreference).where(EmailPreference.user_id == user.id)
        )
    ).scalar_one()
    assert fetched.daily_digest_opt_out is False


async def test_daily_digest_opt_out_round_trips_true(db_session) -> None:
    user = await _user(db_session)
    pref = EmailPreference(
        user_id=user.id,
        daily_reminder=True,
        daily_digest_opt_out=True,
        timezone="UTC",
        unsubscribe_token=secrets.token_hex(32),
    )
    db_session.add(pref)
    await db_session.flush()

    fetched = (
        await db_session.execute(
            select(EmailPreference).where(EmailPreference.user_id == user.id)
        )
    ).scalar_one()
    assert fetched.daily_digest_opt_out is True
