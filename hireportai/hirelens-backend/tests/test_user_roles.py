"""User role & admin RBAC tests.

Covers:
- Unit tests for ``require_admin`` dependency (no DB, no HTTP)
- Integration tests via HTTP client for ``GET /api/v1/auth/me`` (role field)
  and ``GET /api/v1/admin/ping`` (403 for regular users, 200 for admins)

Uses the same ``client`` fixture pattern as ``test_auth.py``.
"""
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.core.deps import get_current_user, require_admin
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helper: create a user via the google auth endpoint
# ---------------------------------------------------------------------------

MOCK_GOOGLE_INFO = {
    "google_id": "role_test_google_id",
    "email": "role_test@example.com",
    "name": "Role Tester",
    "avatar_url": None,
}


async def _sign_in(client) -> tuple[str, str]:
    """Sign in with mocked Google token; return (access_token, user_id)."""
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new_callable=AsyncMock,
        return_value=MOCK_GOOGLE_INFO,
    ):
        resp = await client.post(
            "/api/v1/auth/google",
            json={"credential": "fake-google-credential"},
        )
    assert resp.status_code == 200
    data = resp.json()
    return data["access_token"], data["user"]["id"]


# ---------------------------------------------------------------------------
# Unit tests — call require_admin directly (no HTTP, no DB)
# ---------------------------------------------------------------------------

class TestRequireAdminUnit:
    async def test_passes_for_admin(self):
        """Admin user passes through require_admin without error."""
        admin = User(
            google_id="g1",
            email="a@example.com",
            name="Admin",
            avatar_url=None,
            role="admin",
        )
        # require_admin just wraps get_current_user; call it with user kwarg bypassed
        result = await require_admin(user=admin)
        assert result is admin

    async def test_blocks_regular_user(self):
        """Regular user gets 403 from require_admin."""
        regular = User(
            google_id="g2",
            email="b@example.com",
            name="Bob",
            avatar_url=None,
            role="user",
        )
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=regular)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin access required."

    async def test_unknown_role_is_blocked(self):
        """Any role other than 'admin' (including hypothetical future roles) is blocked."""
        superuser = User(
            google_id="g3",
            email="c@example.com",
            name="Super",
            avatar_url=None,
            role="superadmin",
        )
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=superuser)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Integration tests — HTTP client + real DB session
# ---------------------------------------------------------------------------

class TestGetMeIncludesRole:
    async def test_get_me_returns_role_field(self, client):
        """GET /auth/me response includes ``role`` for a regular user."""
        access_token, _ = await _sign_in(client)
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "role" in data
        assert data["role"] == "user"


class TestAdminPing:
    async def test_regular_user_gets_403(self, client):
        """Non-admin user calling /admin/ping receives 403."""
        access_token, _ = await _sign_in(client)
        resp = await client.get(
            "/api/v1/admin/ping",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin access required."

    async def test_unauthenticated_gets_401(self, client):
        """No token → 401 (auth check runs before role check)."""
        resp = await client.get("/api/v1/admin/ping")
        assert resp.status_code == 401

    async def test_admin_user_gets_200(self, client, db_session):
        """Admin user (role promoted via SQLAlchemy) receives 200 with ok:true."""
        access_token, user_id = await _sign_in(client)

        # Promote the user to admin directly in the test session
        await db_session.execute(
            update(User).where(User.id == user_id).values(role="admin")
        )
        await db_session.flush()

        resp = await client.get(
            "/api/v1/admin/ping",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["role"] == "admin"
