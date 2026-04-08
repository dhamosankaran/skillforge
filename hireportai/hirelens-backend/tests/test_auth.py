"""Auth endpoint tests.

Covers POST /api/v1/auth/google, POST /api/v1/auth/refresh,
POST /api/v1/auth/logout, and GET /api/v1/auth/me.

``verify_google_token`` is an async HTTP call to Google; it is patched with
``AsyncMock`` so these tests run without network access or real credentials.

The ``client`` fixture overrides the FastAPI ``get_db`` dependency to use the
test session (same rollback-on-teardown session from conftest.py).
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token
from app.db.session import get_db
from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    """AsyncClient wired to the test PostgreSQL session.

    Overrides ``get_db`` so every route handler receives the same session
    that the test controls (and that rolls back on teardown).
    """
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _google_user(**overrides) -> dict:
    """Return a fake Google user info dict, optionally customised."""
    base = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@example.com",
        "name": "Test User",
        "avatar_url": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# POST /api/v1/auth/google
# ---------------------------------------------------------------------------

async def test_google_auth_valid_credential(client):
    """Valid credential returns 200 with access_token, refresh_token, and user."""
    user_info = _google_user(email="valid@example.com")
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ):
        resp = await client.post(
            "/api/v1/auth/google", json={"credential": "fake-google-token"}
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == user_info["email"]
    assert "id" in data["user"]


async def test_google_auth_invalid_credential(client):
    """Backend-rejected credential returns 401."""
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.post(
            "/api/v1/auth/google", json={"credential": "bad-token"}
        )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid Google credential"


async def test_google_auth_upserts_existing_user(client):
    """Two sign-ins with the same google_id return the same user.id (upsert)."""
    user_info = _google_user()
    mock = AsyncMock(return_value=user_info)
    with patch("app.api.v1.routes.auth.verify_google_token", new=mock):
        r1 = await client.post("/api/v1/auth/google", json={"credential": "tok1"})
        r2 = await client.post("/api/v1/auth/google", json={"credential": "tok2"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------

async def test_refresh_valid_token(client):
    """Valid refresh token returns a new access token."""
    token = create_refresh_token({"sub": str(uuid.uuid4()), "email": "r@example.com"})
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


async def test_refresh_expired_token(client):
    """Expired refresh token returns 401."""
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": "user-1",
            "email": "e@example.com",
            "type": "refresh",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": expired})
    assert resp.status_code == 401


async def test_refresh_access_token_rejected(client):
    """Submitting an access token (type=access) to /refresh is rejected."""
    access_token = create_access_token(
        {"sub": str(uuid.uuid4()), "email": "a@example.com"}
    )
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------

async def test_get_me_authenticated(client):
    """Valid access token returns user profile and subscription."""
    user_info = _google_user()
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ):
        login = await client.post(
            "/api/v1/auth/google", json={"credential": "tok"}
        )

    access_token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == user_info["email"]
    assert "subscription" in data
    assert data["subscription"]["plan"] == "free"


async def test_get_me_unauthenticated(client):
    """Missing token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_get_me_invalid_token(client):
    """Malformed token returns 401."""
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------

async def test_logout_authenticated(client):
    """Valid token returns 200 with success message."""
    user_info = _google_user()
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ):
        login = await client.post(
            "/api/v1/auth/google", json={"credential": "tok"}
        )

    access_token = login.json()["access_token"]
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged out successfully"


async def test_logout_unauthenticated(client):
    """Missing token returns 401."""
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 401
