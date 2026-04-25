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


async def _seed_feature_log(db_session, user_id: str, feature: str) -> None:
    db_session.add(
        UsageLog(user_id=user_id, feature_used=feature, tokens_consumed=0)
    )
    await db_session.flush()


async def test_usage_requires_auth(client):
    resp = await client.get("/api/v1/payments/usage")
    assert resp.status_code == 401


async def test_usage_free_user_zero_history(client, db_session):
    """Full-shape equality pin: exercises spec #56 §4.3 + spec #58 §5
    flat-extension. A future slice that reshapes the payload will trip
    this assertion and force the spec update to land alongside the code."""
    user = await _seed_user(db_session, plan="free")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "plan": "free",
        "is_admin": False,
        # spec #56 — scans
        "scans_used": 0,
        "scans_remaining": 1,
        "max_scans": 1,
        # spec #58 — rewrites (Pro-only; free = 0/0)
        "rewrites_used": 0,
        "rewrites_remaining": 0,
        "rewrites_max": 0,
        # spec #58 — cover letters (Pro-only; free = 0/0)
        "cover_letters_used": 0,
        "cover_letters_remaining": 0,
        "cover_letters_max": 0,
        # spec #49 §3.4 — interview_prep monthly cap (free = 3/month)
        "interview_preps_used": 0,
        "interview_preps_remaining": 3,
        "interview_preps_max": 3,
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


# ── spec #58 §5 — rewrite + cover-letter counters on /usage ────────────


async def test_usage_free_user_rewrite_and_cover_letter_zeroed(client, db_session):
    """AC-8: free plan sees rewrite + cover-letter buckets as 0/0/0."""
    user = await _seed_user(db_session, plan="free")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["rewrites_used"] == 0
    assert body["rewrites_remaining"] == 0
    assert body["rewrites_max"] == 0
    assert body["cover_letters_used"] == 0
    assert body["cover_letters_remaining"] == 0
    assert body["cover_letters_max"] == 0


async def test_usage_pro_user_rewrite_counter_surfaces_used_unlimited_sentinel(
    client, db_session
):
    """AC-9: Pro user shows the real `used` count but `-1` sentinels for
    `remaining` / `max`. `/rewrite/section` shares the bucket — a single
    `feature_used='rewrite'` row therefore bumps `rewrites_used` to 1
    regardless of which handler wrote it."""
    user = await _seed_user(db_session, plan="pro")
    await _seed_feature_log(db_session, user.id, "rewrite")
    await _seed_feature_log(db_session, user.id, "cover_letter")
    await _seed_feature_log(db_session, user.id, "cover_letter")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["rewrites_used"] == 1
    assert body["rewrites_remaining"] == -1
    assert body["rewrites_max"] == -1
    assert body["cover_letters_used"] == 2
    assert body["cover_letters_remaining"] == -1
    assert body["cover_letters_max"] == -1


async def test_usage_admin_free_plan_rewrite_unlimited_with_is_admin(
    client, db_session
):
    """AC-10: admin-on-free gets `-1` sentinels on every feature counter,
    keeps `plan='free'` + `is_admin=true`."""
    user = await _seed_user(db_session, plan="free", role="admin")
    await _seed_feature_log(db_session, user.id, "rewrite")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["is_admin"] is True
    assert body["rewrites_used"] == 1
    assert body["rewrites_remaining"] == -1
    assert body["rewrites_max"] == -1
    assert body["cover_letters_remaining"] == -1
    assert body["cover_letters_max"] == -1


# ── interview_prep monthly counter on /usage (spec #49 §3.4) ──────────


async def test_usage_free_user_at_interview_prep_cap_shows_zero_remaining(
    client, db_session,
):
    """Free user with 3 interview_prep usage_logs in the current month →
    used=3, remaining=0, max=3. Pre-flight gate signal for Interview.tsx
    derives from these fields; the FE reads `interviewPrepsUsed >=
    interviewPrepsMax` to disable the Generate button before the click.
    """
    user = await _seed_user(db_session, plan="free")
    for _ in range(3):
        await _seed_feature_log(db_session, user.id, "interview_prep")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["interview_preps_used"] == 3
    assert body["interview_preps_remaining"] == 0
    assert body["interview_preps_max"] == 3


async def test_usage_pro_user_interview_prep_unlimited_sentinel(
    client, db_session,
):
    """Pro user shows real used count but `-1` sentinels for remaining/max."""
    user = await _seed_user(db_session, plan="pro")
    await _seed_feature_log(db_session, user.id, "interview_prep")
    await _seed_feature_log(db_session, user.id, "interview_prep")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["interview_preps_used"] == 2
    assert body["interview_preps_remaining"] == -1
    assert body["interview_preps_max"] == -1


async def test_usage_admin_free_plan_interview_prep_unlimited_with_is_admin(
    client, db_session,
):
    """Admin-on-free flips remaining/max to `-1` regardless of plan limit."""
    user = await _seed_user(db_session, plan="free", role="admin")
    await _seed_feature_log(db_session, user.id, "interview_prep")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["is_admin"] is True
    assert body["interview_preps_used"] == 1
    assert body["interview_preps_remaining"] == -1
    assert body["interview_preps_max"] == -1


async def test_usage_free_max_reads_live_from_plan_limits(client, db_session):
    """Free `interview_preps_max` mirrors `PLAN_LIMITS["free"]["interview_prep"]`.

    Guards against regressions where a future tuning of the cap (3 → N) in
    `usage_service.PLAN_LIMITS` is silently inconsistent with the snapshot
    response. If this fails after a cap change, both the constant and this
    pin update together.
    """
    from app.services.usage_service import PLAN_LIMITS

    user = await _seed_user(db_session, plan="free")
    resp = await client.get("/api/v1/payments/usage", headers=_auth(user))
    assert resp.status_code == 200
    assert resp.json()["interview_preps_max"] == PLAN_LIMITS["free"]["interview_prep"]
