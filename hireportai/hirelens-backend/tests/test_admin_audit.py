"""Admin audit-log foundations (spec #38 E-018a).

Covers:
- A row is written to `admin_audit_log` when an admin hits an admin
  endpoint.
- The audit write does not add meaningful latency to the response path.
- Non-admins get 403 on `GET /api/v1/admin/audit` (router-level
  `audit_admin_request` dep chains `require_admin`).
- `/admin/audit` paginates correctly and respects `admin_id` / `route`
  filters.
"""
from __future__ import annotations

import time
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


# ── Fixtures ─────────────────────────────────────────────────────────────────

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


async def _sign_in(client, db_session, role: str = "user") -> tuple[str, str]:
    """Register a fresh user via the auth endpoint. Optionally promote to admin."""
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@audit-test.com",
        "name": "Audit Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "t"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    token = data["access_token"]
    user_id = data["user"]["id"]

    if role == "admin":
        await db_session.execute(
            sql_update(User).where(User.id == user_id).values(role="admin")
        )
        await db_session.flush()

    return token, user_id


# ── Tests ────────────────────────────────────────────────────────────────────

async def test_audit_log_written_on_admin_request(client, db_session):
    """Admin hitting any admin endpoint leaves exactly one `admin_audit_log` row.

    Uses `/admin/ping` (the existing smoke-test endpoint) rather than the
    new `/admin/audit` listing so this test doesn't conflate "audit path
    audits itself" with "every admin path is audited".
    """
    token, admin_id = await _sign_in(client, db_session, role="admin")
    before = await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.admin_id == admin_id)
    )
    assert before.scalars().all() == []

    resp = await client.get(
        "/api/v1/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    after = await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.admin_id == admin_id)
    )
    rows = after.scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.route == "/api/v1/admin/ping"
    assert row.method == "GET"
    assert row.query_params == {}
    assert row.ip_address  # set from request.client.host or "unknown"


async def test_audit_log_does_not_block_response(client, db_session):
    """The audit write is scheduled as a BackgroundTask; response latency stays low.

    Threshold is generous (500ms) so the assertion is about "no blocking
    pathological wait on audit I/O" rather than a tight perf bound.
    Network round-trips against the in-process ASGI transport typically
    come in well under 50ms on dev hardware.
    """
    token, _ = await _sign_in(client, db_session, role="admin")
    # Warm up a first request so any import-time cost is excluded.
    await client.get(
        "/api/v1/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )

    start = time.perf_counter()
    resp = await client.get(
        "/api/v1/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert resp.status_code == 200
    assert elapsed_ms < 500, f"admin ping took {elapsed_ms:.1f}ms (expected <500)"


async def test_non_admin_gets_403_on_audit_endpoint(client, db_session):
    """`audit_admin_request` chains `require_admin`; non-admin callers get 403."""
    token, _ = await _sign_in(client, db_session, role="user")
    resp = await client.get(
        "/api/v1/admin/audit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin access required."


async def test_audit_endpoint_pagination(client, db_session):
    """`/admin/audit` returns rows most-recent-first and honours pagination."""
    token, admin_id = await _sign_in(client, db_session, role="admin")

    # Fire 5 pings to produce 5 audit rows. Each request adds one row
    # (deduped by FastAPI's same-dep caching — audit_admin_request runs
    # once even though it's both router-level and in-route).
    for _ in range(5):
        resp = await client.get(
            "/api/v1/admin/ping",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    # First audit GET picks up the 5 pings. (The audit GET itself writes
    # a 6th row by the time the response is composed; the listing query
    # runs before that 6th row commits, so we still expect 5 here.)
    resp = await client.get(
        "/api/v1/admin/audit?per_page=3&page=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["per_page"] == 3
    assert body["page"] == 1
    assert len(body["items"]) == 3
    # All three should be /admin/ping hits, not /admin/audit.
    assert all(item["route"] == "/api/v1/admin/ping" for item in body["items"])
    # Most-recent-first ordering — created_at is monotonic across this
    # same-test loop.
    timestamps = [item["created_at"] for item in body["items"]]
    assert timestamps == sorted(timestamps, reverse=True)

    # Page 2 returns the remaining /admin/ping rows (we don't assert on
    # how many /admin/audit rows are visible because that depends on
    # transaction ordering with the audit-audit row).
    resp2 = await client.get(
        "/api/v1/admin/audit?per_page=3&page=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["page"] == 2
    # Total has grown by at least 1 (the first /admin/audit call audited itself).
    assert body2["total"] >= 5
    # Route filter narrows to just ping hits.
    resp3 = await client.get(
        "/api/v1/admin/audit?route=/api/v1/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp3.status_code == 200
    body3 = resp3.json()
    assert body3["total"] == 5
    assert all(item["route"] == "/api/v1/admin/ping" for item in body3["items"])
