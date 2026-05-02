"""HTTP contract tests for /api/v1/email-preferences slice 6.13 extension.

Spec: docs/specs/phase-6/13-pro-digest-opt-out.md §10.1 +
AC-1..AC-5 + AC-15 + AC-16.
"""
from __future__ import annotations

import secrets
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.email_preference import EmailPreference
from app.models.subscription import Subscription
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _seed_user(
    db_session, *, plan: str | None = None, role: str = "user"
) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@email-prefs-route.test",
        name="Prefs Route Tester",
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    if plan is not None:
        db_session.add(
            Subscription(user_id=user.id, plan=plan, status="active")
        )
        await db_session.flush()
    await db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    tok = create_access_token({"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {tok}"}


async def _fetch_pref(db_session, user_id: str) -> EmailPreference | None:
    return (
        await db_session.execute(
            select(EmailPreference).where(EmailPreference.user_id == user_id)
        )
    ).scalar_one_or_none()


async def test_get_returns_daily_digest_opt_out_for_free_user(
    client, db_session
) -> None:
    user = await _seed_user(db_session, plan="free")
    resp = await client.get(
        "/api/v1/email-preferences", headers=_auth(user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["daily_digest_opt_out"] is False
    assert body["daily_reminder"] is True


async def test_get_returns_daily_digest_opt_out_for_pro_user(
    client, db_session
) -> None:
    user = await _seed_user(db_session, plan="pro")
    resp = await client.get(
        "/api/v1/email-preferences", headers=_auth(user)
    )
    assert resp.status_code == 200
    assert resp.json()["daily_digest_opt_out"] is False


async def test_pro_user_can_set_digest_opt_out(client, db_session) -> None:
    user = await _seed_user(db_session, plan="pro")
    resp = await client.put(
        "/api/v1/email-preferences",
        json={"daily_digest_opt_out": True},
        headers=_auth(user),
    )
    assert resp.status_code == 200
    assert resp.json()["daily_digest_opt_out"] is True
    pref = await _fetch_pref(db_session, user.id)
    assert pref is not None
    assert pref.daily_digest_opt_out is True


async def test_enterprise_user_can_set_digest_opt_out(
    client, db_session
) -> None:
    user = await _seed_user(db_session, plan="enterprise")
    resp = await client.put(
        "/api/v1/email-preferences",
        json={"daily_digest_opt_out": True},
        headers=_auth(user),
    )
    assert resp.status_code == 200
    assert resp.json()["daily_digest_opt_out"] is True


async def test_free_user_digest_opt_out_returns_403(client, db_session) -> None:
    user = await _seed_user(db_session, plan="free")
    resp = await client.put(
        "/api/v1/email-preferences",
        json={"daily_digest_opt_out": True},
        headers=_auth(user),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == (
        "Daily digest opt-out requires a Pro subscription"
    )
    pref = await _fetch_pref(db_session, user.id)
    # Either no row was created or, if one was, the column stays default.
    if pref is not None:
        assert pref.daily_digest_opt_out is False


async def test_user_with_no_subscription_digest_opt_out_returns_403(
    client, db_session
) -> None:
    user = await _seed_user(db_session, plan=None)
    resp = await client.put(
        "/api/v1/email-preferences",
        json={"daily_digest_opt_out": True},
        headers=_auth(user),
    )
    assert resp.status_code == 403


async def test_free_user_can_still_toggle_daily_reminder(
    client, db_session
) -> None:
    user = await _seed_user(db_session, plan="free")
    resp = await client.put(
        "/api/v1/email-preferences",
        json={"daily_reminder": False},
        headers=_auth(user),
    )
    assert resp.status_code == 200
    assert resp.json()["daily_reminder"] is False


async def test_admin_on_free_plan_can_set_digest_opt_out(
    client, db_session
) -> None:
    user = await _seed_user(db_session, plan="free", role="admin")
    resp = await client.put(
        "/api/v1/email-preferences",
        json={"daily_digest_opt_out": True},
        headers=_auth(user),
    )
    assert resp.status_code == 200
    assert resp.json()["daily_digest_opt_out"] is True


async def test_unsubscribe_token_unwritten_by_route(client, db_session) -> None:
    """AC-15 regression guard — route never writes ``unsubscribe_token``."""
    user = await _seed_user(db_session, plan="pro")
    pref_seed = EmailPreference(
        user_id=user.id,
        daily_reminder=True,
        timezone="UTC",
        unsubscribe_token=secrets.token_hex(32),
    )
    db_session.add(pref_seed)
    await db_session.flush()
    original_token = pref_seed.unsubscribe_token

    resp = await client.put(
        "/api/v1/email-preferences",
        json={"daily_digest_opt_out": True},
        headers=_auth(user),
    )
    assert resp.status_code == 200
    pref = await _fetch_pref(db_session, user.id)
    assert pref is not None
    assert pref.unsubscribe_token == original_token
