"""Spec #56 — HTTP contract tests for GET /api/v1/payments/usage.

Covers AC-1..AC-7 response-shape claims and the is_admin extension to
§4.3.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
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
    db_session, *, plan: str = "free", role: str = "user"
) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Usage Route Test",
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Subscription(user_id=user.id, plan=plan, status="active"))
    await db_session.flush()
    await db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    tok = create_access_token({"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {tok}"}


async def _seed_analyze_log(db_session, user_id: str) -> None:
    db_session.add(UsageLog(user_id=user_id, feature_used="analyze", tokens_consumed=0))
    await db_session.flush()


async def test_usage_requires_auth(client):
    resp = await client.get("/api/v1/payments/usage")
    assert resp.status_code == 401


async def test_usage_free_user_zero_history(client, db_session):
    user = await _seed_user(db_session, plan="free")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "plan": "free",
        "scans_used": 0,
        "scans_remaining": 1,
        "max_scans": 1,
        "is_admin": False,
    }


async def test_usage_free_user_after_one_scan_shows_cap_reached(client, db_session):
    user = await _seed_user(db_session, plan="free")
    await _seed_analyze_log(db_session, user.id)
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["scans_used"] == 1
    assert body["scans_remaining"] == 0
    assert body["max_scans"] == 1
    assert body["is_admin"] is False


async def test_usage_pro_user_unlimited_sentinel(client, db_session):
    user = await _seed_user(db_session, plan="pro")
    await _seed_analyze_log(db_session, user.id)
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["scans_used"] == 1
    assert body["scans_remaining"] == -1
    assert body["max_scans"] == -1
    assert body["is_admin"] is False


async def test_usage_admin_free_plan_unlimited_is_admin_true(client, db_session):
    """Admin-on-free-plan: plan stays 'free'; is_admin=true; unlimited."""
    user = await _seed_user(db_session, plan="free", role="admin")
    await _seed_analyze_log(db_session, user.id)
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["scans_used"] == 1
    assert body["scans_remaining"] == -1
    assert body["max_scans"] == -1
    assert body["is_admin"] is True


async def test_usage_enterprise_is_admin_false_and_unlimited(client, db_session):
    user = await _seed_user(db_session, plan="enterprise")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "enterprise"
    assert body["scans_remaining"] == -1
    assert body["max_scans"] == -1
    assert body["is_admin"] is False
