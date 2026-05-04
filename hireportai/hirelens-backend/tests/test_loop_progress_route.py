"""Integration tests for `GET /api/v1/learn/loop-progress` (spec #66 §6.1).

Mirrors the test_dashboard_routes.py ASGI-client + auth-via-google-mock
pattern.
"""
from __future__ import annotations

import json
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.tracker import TrackerApplicationModel
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
        "email": f"{uuid.uuid4()}@loop-route-test.com",
        "name": "Loop Route Tester",
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


async def _seed_tracker(
    db_session,
    user_id: str,
    *,
    skills_missing: list[str] | None = None,
) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company="Acme",
        role="Engineer",
        date_applied=date.today().isoformat(),
        ats_score=72,
        scan_id=str(uuid.uuid4()),
        skills_missing=json.dumps(skills_missing) if skills_missing else None,
    )
    db_session.add(row)
    await db_session.flush()
    return row


# ── 1. Auth gate ─────────────────────────────────────────────────────────────


async def test_loop_progress_unauthed_returns_401(client, db_session):
    resp = await client.get(
        "/api/v1/learn/loop-progress",
        params={"tracker_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


# ── 2. Missing query param → 422 ────────────────────────────────────────────


async def test_loop_progress_missing_tracker_id_returns_422(client, db_session):
    token, _ = await _sign_in(client)
    resp = await client.get(
        "/api/v1/learn/loop-progress",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ── 3. Cross-user tracker → 404 ─────────────────────────────────────────────


async def test_loop_progress_cross_user_returns_404(client, db_session):
    """Another user's tracker_id must not leak progress data."""
    token, _ = await _sign_in(client)
    other = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@other-loop.com",
        name="Other",
        persona="interview_prepper",
        onboarding_completed=True,
    )
    db_session.add(other)
    await db_session.flush()
    other_tracker = await _seed_tracker(db_session, other.id)

    resp = await client.get(
        "/api/v1/learn/loop-progress",
        params={"tracker_id": other_tracker.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── 4. Happy path: zero-gap returns zeros + null days_since_last_scan ───────


async def test_loop_progress_authed_zero_gap_returns_zeros(client, db_session):
    token, user_id = await _sign_in(client)
    tracker = await _seed_tracker(db_session, user_id, skills_missing=None)

    resp = await client.get(
        "/api/v1/learn/loop-progress",
        params={"tracker_id": tracker.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tracker_application_id"] == tracker.id
    assert body["total_gap_cards"] == 0
    assert body["reviewed_gap_cards"] == 0
    assert body["percent_reviewed"] == 0.0
    assert body["days_since_last_scan"] is None
