"""Integration tests for `GET /api/v1/learn/dashboard`.

Spec: docs/specs/phase-6/09-fsrs-dashboard.md §10.2 + AC-1..AC-3 +
§12 D-3 / D-7 / D-14.

Mirrors the test_ranker_routes.py ASGI client + auth-via-google-mock
pattern.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _sign_in(client) -> tuple[str, str]:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@dashboard-route-test.com",
        "name": "Dashboard Route Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["access_token"], data["user"]["id"]


async def _set_persona(db_session, user_id: str, persona: str) -> None:
    user = await db_session.get(User, user_id)
    user.persona = persona
    await db_session.flush()


# ── 1. Auth gate (AC-1) ─────────────────────────────────────────────────────


async def test_get_dashboard_unauthed_returns_401(client, db_session):
    resp = await client.get("/api/v1/learn/dashboard")
    assert resp.status_code == 401


# ── 2. Authed cold-start (AC-2) ─────────────────────────────────────────────


async def test_get_dashboard_authed_fresh_user_returns_cold_start(
    client, db_session
):
    token, user_id = await _sign_in(client)
    await _set_persona(db_session, user_id, "interview_prepper")

    resp = await client.get(
        "/api/v1/learn/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["is_cold_start"] is True
    assert body["retention_window_days"] == 30  # D-7 default
    assert body["cards_due"]["total_quiz_items_in_progress"] == 0
    assert body["retention"]["sample_size"] == 0
    assert body["review_history"]["total_in_window"] == 0


# ── 3. Custom retention window query param (D-14) ───────────────────────────


async def test_get_dashboard_honors_retention_window_query_param(
    client, db_session
):
    token, _ = await _sign_in(client)
    resp = await client.get(
        "/api/v1/learn/dashboard?retention_window_days=7",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["retention_window_days"] == 7
    assert len(body["retention"]["daily_retention"]) == 7


# ── 4. Out-of-range retention_window_days returns 422 (Pydantic validator) ──


async def test_get_dashboard_invalid_retention_window_returns_422(
    client, db_session
):
    token, _ = await _sign_in(client)
    resp = await client.get(
        "/api/v1/learn/dashboard?retention_window_days=999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ── 5. Response shape regression ────────────────────────────────────────────


async def test_get_dashboard_response_shape_is_envelope(client, db_session):
    """D-3 single-envelope: every section keyed at top level."""
    token, _ = await _sign_in(client)
    resp = await client.get(
        "/api/v1/learn/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "user_id",
        "persona",
        "plan",
        "is_cold_start",
        "retention_window_days",
        "generated_at",
        "cards_due",
        "retention",
        "deck_mastery",
        "streak",
        "review_history",
    ):
        assert key in body, f"missing top-level key: {key}"
