"""Tests for IP-based registration limiting.

Verifies that new account creation is blocked after 2 registrations from
the same IP within 30 days, while existing user logins are never blocked.
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.db.session import get_db
from app.main import app
from app.models.registration_log import RegistrationLog

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEST_IP = "203.0.113.42"


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


def _google_user(**overrides) -> dict:
    base = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@example.com",
        "name": "Test User",
        "avatar_url": None,
    }
    base.update(overrides)
    return base


async def _register(client, user_info, ip=TEST_IP):
    """POST /auth/google with a specific IP via X-Forwarded-For."""
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ):
        return await client.post(
            "/api/v1/auth/google",
            json={"credential": "fake-token"},
            headers={"X-Forwarded-For": ip},
        )


async def test_first_registration_from_ip_succeeds(client):
    """First new account from an IP should succeed."""
    ip = f"10.1.{uuid.uuid4().int % 256}.1"
    user_info = _google_user()
    resp = await _register(client, user_info, ip=ip)
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == user_info["email"]


async def test_second_registration_same_ip_succeeds(client):
    """Second new account from the same IP should still succeed."""
    ip = f"10.2.{uuid.uuid4().int % 256}.1"
    # First registration
    resp1 = await _register(client, _google_user(), ip=ip)
    assert resp1.status_code == 200
    # Second registration — should still work
    resp2 = await _register(client, _google_user(), ip=ip)
    assert resp2.status_code == 200


async def test_third_registration_same_ip_returns_403(client):
    """Third new account from the same IP within 30 days should be blocked."""
    ip = f"10.3.{uuid.uuid4().int % 256}.1"
    # Register 2 accounts
    resp1 = await _register(client, _google_user(), ip=ip)
    assert resp1.status_code == 200
    resp2 = await _register(client, _google_user(), ip=ip)
    assert resp2.status_code == 200
    # Third should be blocked
    resp3 = await _register(client, _google_user(), ip=ip)
    assert resp3.status_code == 403
    body = resp3.json()
    assert body["detail"]["code"] == "IP_LIMIT_REACHED"


async def test_existing_user_login_from_blocked_ip_succeeds(client):
    """An existing user should always be able to log in, even from a blocked IP."""
    ip = f"10.4.{uuid.uuid4().int % 256}.1"
    # Create a user from a clean IP
    user_info = _google_user()
    resp = await _register(client, user_info, ip="172.16.0.1")
    assert resp.status_code == 200

    # Burn out the IP limit
    await _register(client, _google_user(), ip=ip)
    await _register(client, _google_user(), ip=ip)

    # Existing user logs in from the blocked IP — should succeed
    resp2 = await _register(client, user_info, ip=ip)
    assert resp2.status_code == 200
    assert resp2.json()["user"]["email"] == user_info["email"]


async def test_registration_from_different_ip_succeeds(client):
    """A new account from a different IP should succeed regardless of blocks elsewhere."""
    ip = f"10.5.{uuid.uuid4().int % 256}.1"
    user_info = _google_user()
    resp = await _register(client, user_info, ip=ip)
    assert resp.status_code == 200


async def test_old_registrations_beyond_30_days_dont_count(client, db_session):
    """Registrations older than 30 days should not count toward the limit."""
    ip = f"10.6.{uuid.uuid4().int % 256}.1"

    # Create 2 accounts from this IP (fills the limit)
    resp1 = await _register(client, _google_user(), ip=ip)
    assert resp1.status_code == 200
    resp2 = await _register(client, _google_user(), ip=ip)
    assert resp2.status_code == 200

    # Backdate all registration logs for this IP to 60 days ago
    await db_session.execute(
        update(RegistrationLog)
        .where(RegistrationLog.ip_address == ip)
        .values(created_at=datetime.utcnow() - timedelta(days=60))
    )
    await db_session.flush()

    # A 3rd registration should now succeed (old ones are outside the 30-day window)
    resp3 = await _register(client, _google_user(), ip=ip)
    assert resp3.status_code == 200
