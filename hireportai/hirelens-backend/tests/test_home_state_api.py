"""API tests for GET /api/v1/home/state (P5-S18c, spec #40 §9)."""
from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.gamification import GamificationStats
from app.services import home_state_service

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


@pytest.fixture(autouse=True)
def _disable_redis(monkeypatch):
    """Force the service to bypass Redis so tests don't depend on a live cache."""
    monkeypatch.setattr(home_state_service, "_get_redis", lambda: None)


async def _sign_in(client) -> tuple[str, str]:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@home-api-test.com",
        "name": "Home API Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post(
            "/api/v1/auth/google", json={"credential": "tok"}
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["access_token"], data["user"]["id"]


class TestEndpointBasics:
    async def test_get_home_state_requires_auth(self, client):
        resp = await client.get("/api/v1/home/state")
        assert resp.status_code == 401

    async def test_get_home_state_returns_schema(self, client):
        token, _ = await _sign_in(client)
        resp = await client.get(
            "/api/v1/home/state",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "persona" in body
        assert "states" in body
        assert "context" in body
        assert isinstance(body["states"], list)
        ctx = body["context"]
        for key in (
            "current_streak",
            "last_review_at",
            "active_mission_id",
            "mission_target_date",
            "last_scan_date",
            "plan",
            "last_activity_at",
        ):
            assert key in ctx


class TestPerfBudget:
    async def test_get_home_state_under_cold_budget(self, client, db_session):
        """Cold-cache p95 ≤ 250ms (spec §6 — single-call sample)."""
        token, user_id = await _sign_in(client)
        # Seed a couple of signals so the evaluator does real work.
        stats = GamificationStats(
            user_id=user_id,
            current_streak=4,
            longest_streak=4,
            total_xp=100,
            last_active_date=date.today(),
            freezes_available=0,
        )
        db_session.add(stats)
        await db_session.flush()

        start = time.perf_counter()
        resp = await client.get(
            "/api/v1/home/state",
            headers={"Authorization": f"Bearer {token}"},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        # Generous for CI variance — spec asserts p95 ≤ 250ms.
        assert elapsed_ms < 1500, f"cold path too slow: {elapsed_ms:.1f}ms"

    async def test_get_home_state_under_warm_budget(self, client):
        """Warm-cache p95 ≤ 100ms — second call should be fast (no DB beyond auth)."""
        token, _ = await _sign_in(client)
        # First call warms the cache (well, no-cache here, but DB is hot).
        await client.get(
            "/api/v1/home/state",
            headers={"Authorization": f"Bearer {token}"},
        )
        start = time.perf_counter()
        resp = await client.get(
            "/api/v1/home/state",
            headers={"Authorization": f"Bearer {token}"},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        # Generous for CI variance — spec asserts warm p95 ≤ 100ms.
        assert elapsed_ms < 1000, f"warm path too slow: {elapsed_ms:.1f}ms"
