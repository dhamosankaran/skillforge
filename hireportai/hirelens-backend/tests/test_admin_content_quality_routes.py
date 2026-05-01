"""Admin content-quality route tests (Phase 6 slice 6.11 — B-084).

Spec: docs/specs/phase-6/11-content-quality-retention.md §10.2 +
§11 AC-1 / AC-2 / AC-3 / AC-10 / AC-16.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update as sql_update

from app.db.session import get_db
from app.main import app
from app.models.admin_audit_log import AdminAuditLog
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


async def _sign_in_admin(client, db_session) -> tuple[str, str]:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@admin-cq-test.com",
        "name": "Admin CQ Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200
    data = resp.json()
    user_id = data["user"]["id"]
    await db_session.execute(
        sql_update(User).where(User.id == user_id).values(role="admin")
    )
    await db_session.flush()
    return data["access_token"], user_id


async def _sign_in_user(client) -> str:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@user-cq-test.com",
        "name": "Plain User",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ── 1. AC-1 unauthed → 401 ──────────────────────────────────────────────────


async def test_unauthed_get_returns_401(client):
    resp = await client.get("/api/v1/admin/content-quality")
    assert resp.status_code == 401


# ── 2. AC-2 non-admin authed → 403 ──────────────────────────────────────────


async def test_non_admin_get_returns_403(client, db_session):
    token = await _sign_in_user(client)
    resp = await client.get(
        "/api/v1/admin/content-quality",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── 3. AC-3 admin happy path → 200 + envelope shape ─────────────────────────


async def test_admin_happy_path_returns_200_envelope(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    resp = await client.get(
        "/api/v1/admin/content-quality",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Envelope shape — all sections present even on cold start.
    for key in (
        "window_days",
        "include_archived",
        "generated_at",
        "is_cold_start",
        "decks",
        "worst_lessons",
        "worst_quiz_items",
        "writebacks_applied",
    ):
        assert key in body
    assert body["window_days"] == 30
    assert body["include_archived"] is False


# ── 4. AC-10 window clamp — out-of-range → 422 ──────────────────────────────


async def test_window_days_above_max_returns_422(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    resp = await client.get(
        "/api/v1/admin/content-quality?window_days=200",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_window_days_below_min_returns_422(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    resp = await client.get(
        "/api/v1/admin/content-quality?window_days=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ── 5. include_archived=true honoured ───────────────────────────────────────


async def test_include_archived_true_passed_through(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    resp = await client.get(
        "/api/v1/admin/content-quality?include_archived=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["include_archived"] is True


# ── 6. AC-16 admin_audit_log row written ────────────────────────────────────


async def test_admin_audit_log_row_written_per_request(client, db_session):
    token, admin_id = await _sign_in_admin(client, db_session)
    resp = await client.get(
        "/api/v1/admin/content-quality",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    rows = (
        await db_session.execute(
            select(AdminAuditLog).where(
                AdminAuditLog.admin_id == admin_id,
                AdminAuditLog.route == "/api/v1/admin/content-quality",
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
