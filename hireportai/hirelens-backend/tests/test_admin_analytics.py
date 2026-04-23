"""Admin analytics — metrics + performance (spec #38 E-018b slice 2/4).

Covers:
- `/admin/analytics/metrics` shape + six-OKR presence + 7d/30d delta math
- Divide-by-zero delta safety
- Redis cache hit path (bypasses DB on second call)
- `/admin/analytics/performance` shape + LLM spend from `usage_logs` +
  webhook availability marker
- 403 for non-admins on both endpoints
- 422 on malformed date params
- `admin_analytics_viewed` fires via `audit_admin_request` side-channel
  when the path is under `/api/v1/admin/analytics/*` (Slice 1 emitter
  activates here in Slice 2).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update as sql_update

from app.db.session import get_db
from app.main import app
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User
from app.services import admin_analytics_service

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
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@analytics-test.com",
        "name": "Analytics Tester",
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


# Disable Redis for every test in this module — _get_redis returning None
# forces the service to compute fresh on every call, which is what most
# tests want. The cache-hit test re-patches with a dict-backed fake.
@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def _disable_admin_analytics_cache():
    with patch(
        "app.services.admin_analytics_service._get_redis", return_value=None
    ):
        yield


# ── Metrics tests ────────────────────────────────────────────────────────────

async def test_metrics_shape_and_six_okrs(client, db_session):
    """Admin hits /metrics; response contains all six OKRs with full MetricValue shape."""
    token, _ = await _sign_in(client, db_session, role="admin")
    resp = await client.get(
        "/api/v1/admin/analytics/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for okr in (
        "registered_users",
        "paying_pro_users",
        "dau_mau_ratio",
        "avg_streak_length",
        "ats_to_pro_conversion",
        "monthly_churn",
    ):
        assert okr in body, f"missing OKR: {okr}"
        tile = body[okr]
        for field in ("current", "d7_ago", "d30_ago", "delta_7d_pct", "delta_30d_pct"):
            assert field in tile, f"{okr} missing field {field}"
    assert body["from_cache"] is False
    assert "generated_at" in body


async def test_metrics_divide_by_zero_delta(client, db_session):
    """Freshly seeded DB: zero users 30d ago. Delta must be 0.0, not `inf`."""
    token, _ = await _sign_in(client, db_session, role="admin")
    resp = await client.get(
        "/api/v1/admin/analytics/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = resp.json()
    # registered_users: d30_ago will be 0 on a fresh DB; delta must not be inf.
    reg = body["registered_users"]
    # delta is always finite (0.0 when past == 0)
    assert reg["delta_7d_pct"] == 0.0 or isinstance(reg["delta_7d_pct"], float)
    assert reg["delta_30d_pct"] == 0.0 or isinstance(reg["delta_30d_pct"], float)
    # Never inf
    import math
    assert not math.isinf(reg["delta_7d_pct"])
    assert not math.isinf(reg["delta_30d_pct"])


async def test_metrics_cache_hit_short_circuits(client, db_session):
    """With a fake Redis that stores + returns payloads, second call sets from_cache=True."""
    token, _ = await _sign_in(client, db_session, role="admin")

    # Minimal dict-backed Redis stand-in with get/setex.
    store: dict[str, str] = {}

    class FakeRedis:
        def get(self, key):
            return store.get(key)

        def setex(self, key, ttl, value):
            store[key] = value

        def ping(self):
            return True

    fake = FakeRedis()
    with patch(
        "app.services.admin_analytics_service._get_redis", return_value=fake
    ):
        first = await client.get(
            "/api/v1/admin/analytics/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first.status_code == 200
        assert first.json()["from_cache"] is False

        second = await client.get(
            "/api/v1/admin/analytics/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == 200
        assert second.json()["from_cache"] is True


# ── Performance tests ────────────────────────────────────────────────────────

async def test_performance_shape_and_availability_markers(client, db_session):
    """Deferred fields are null / empty, marker fields are False, live fields are numbers."""
    token, _ = await _sign_in(client, db_session, role="admin")
    resp = await client.get(
        "/api/v1/admin/analytics/performance",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["llm_spend_estimate_usd"], (int, float))
    assert isinstance(body["llm_spend_breakdown"], dict)
    assert body["api_latency"] == []
    assert body["api_latency_available"] is False
    assert body["error_rate_24h_pct"] is None
    assert body["error_rate_available"] is False
    # stripe_webhook_*_pct is None when no rows exist in the 24h window, which
    # is true of a freshly seeded DB.
    assert body["stripe_webhook_success_24h_pct"] is None
    assert body["stripe_webhook_available"] is False
    assert body["from_cache"] is False


async def test_performance_llm_spend_from_usage_logs(client, db_session):
    """Seed a 1,000,000-token `resume_optimize` row → spend == reasoning tier rate."""
    token, admin_id = await _sign_in(client, db_session, role="admin")
    # Create a row this month with exactly 1M tokens attributed to
    # resume_optimize (maps to reasoning tier).
    log = UsageLog(
        user_id=admin_id,
        feature_used="resume_optimize",
        tokens_consumed=1_000_000,
    )
    db_session.add(log)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/admin/analytics/performance",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = resp.json()
    # Reasoning price is 5.00/1M per llm_router.TIER_PRICE_USD_PER_1M_TOKENS.
    from app.core.llm_router import TIER_PRICE_USD_PER_1M_TOKENS
    expected = TIER_PRICE_USD_PER_1M_TOKENS["reasoning"]
    assert body["llm_spend_estimate_usd"] == pytest.approx(expected, rel=1e-6)
    assert body["llm_spend_breakdown"]["resume_optimize"] == pytest.approx(
        expected, rel=1e-6
    )


# ── Auth / validation ────────────────────────────────────────────────────────

async def test_non_admin_gets_403_on_metrics(client, db_session):
    """`audit_admin_request` chains `require_admin`; non-admin → 403."""
    token, _ = await _sign_in(client, db_session, role="user")
    resp = await client.get(
        "/api/v1/admin/analytics/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin access required."


async def test_non_admin_gets_403_on_performance(client, db_session):
    token, _ = await _sign_in(client, db_session, role="user")
    resp = await client.get(
        "/api/v1/admin/analytics/performance",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_invalid_to_date_rejected_422(client, db_session):
    token, _ = await _sign_in(client, db_session, role="admin")
    resp = await client.get(
        "/api/v1/admin/analytics/metrics?to=not-a-date",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_invalid_from_date_rejected_422(client, db_session):
    token, _ = await _sign_in(client, db_session, role="admin")
    resp = await client.get(
        "/api/v1/admin/analytics/performance?from=nope",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ── admin_analytics_viewed emitter ───────────────────────────────────────────

async def test_admin_analytics_viewed_fires_on_success(client, db_session):
    """Slice 1 emitter was dormant; Slice 2 path triggers it on every admin hit.

    Patched at the side-fire helper in `app.core.deps` (the BackgroundTask
    target) so the test sees the call without needing a live PostHog client.
    """
    token, admin_id = await _sign_in(client, db_session, role="admin")
    with patch("app.core.deps._fire_admin_analytics_viewed") as fire:
        resp = await client.get(
            "/api/v1/admin/analytics/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
    # BackgroundTasks invokes the callable synchronously on ASGITransport;
    # one call per request.
    assert fire.called, "admin_analytics_viewed not scheduled"
    args, _ = fire.call_args
    assert args[0] == admin_id
    assert args[1] == "/api/v1/admin/analytics/metrics"


async def test_admin_analytics_viewed_not_fired_on_non_analytics_admin_path(
    client, db_session
):
    """Regression guard: the emitter only fires for paths under /admin/analytics/*."""
    token, _ = await _sign_in(client, db_session, role="admin")
    with patch("app.core.deps._fire_admin_analytics_viewed") as fire:
        resp = await client.get(
            "/api/v1/admin/ping",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
    assert not fire.called
