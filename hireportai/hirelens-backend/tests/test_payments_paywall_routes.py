"""Spec #42 — HTTP contract tests for the two paywall-dismissal endpoints.

Covers POST /api/v1/payments/paywall-dismiss and
GET /api/v1/payments/should-show-paywall. Win-back surface is deferred,
so no email-send mocks and no win_back_eligible assertions.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.subscription import Subscription
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
        name="Route Test",
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


# ── POST /paywall-dismiss ───────────────────────────────────────────────────


async def test_dismiss_unauthenticated_returns_401(client):
    resp = await client.post(
        "/api/v1/payments/paywall-dismiss",
        json={"trigger": "daily_review"},
    )
    assert resp.status_code == 401


async def test_dismiss_invalid_trigger_returns_422(client, db_session):
    user = await _seed_user(db_session)
    # Empty trigger
    resp = await client.post(
        "/api/v1/payments/paywall-dismiss",
        headers=_auth(user),
        json={"trigger": ""},
    )
    assert resp.status_code == 422

    # Trigger too long (>64 chars)
    resp = await client.post(
        "/api/v1/payments/paywall-dismiss",
        headers=_auth(user),
        json={"trigger": "x" * 65},
    )
    assert resp.status_code == 422

    # Missing trigger entirely
    resp = await client.post(
        "/api/v1/payments/paywall-dismiss",
        headers=_auth(user),
        json={},
    )
    assert resp.status_code == 422


async def test_dismiss_happy_path_returns_200_and_logs(client, db_session):
    user = await _seed_user(db_session)
    with patch(
        "app.api.routes.payments.analytics_track"
    ) as mock_track:
        resp = await client.post(
            "/api/v1/payments/paywall-dismiss",
            headers=_auth(user),
            json={"trigger": "daily_review", "action_count_at_dismissal": 1},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["logged"] is True
    assert data["dismissal_id"]
    assert data["dismissals_in_window"] == 1
    # No win_back_eligible field — deferred per Path B re-scoping.
    assert "win_back_eligible" not in data

    mock_track.assert_called_once()
    call = mock_track.call_args
    assert call.kwargs["event"] == "paywall_dismissed"
    assert call.kwargs["properties"]["trigger"] == "daily_review"
    assert call.kwargs["properties"]["dismissals_in_window"] == 1
    assert call.kwargs["properties"]["action_count_at_dismissal"] == 1


async def test_dismiss_idempotent_within_window(client, db_session):
    user = await _seed_user(db_session)
    with patch("app.api.routes.payments.analytics_track") as mock_track:
        first = await client.post(
            "/api/v1/payments/paywall-dismiss",
            headers=_auth(user),
            json={"trigger": "daily_review"},
        )
        second = await client.post(
            "/api/v1/payments/paywall-dismiss",
            headers=_auth(user),
            json={"trigger": "daily_review"},
        )
    assert first.status_code == 200 and second.status_code == 200
    a, b = first.json(), second.json()
    assert a["logged"] is True
    assert b["logged"] is False
    assert b["dismissal_id"] == a["dismissal_id"]
    assert b["dismissals_in_window"] == 1

    # Event fires once — dedup'd response should not re-emit.
    assert mock_track.call_count == 1


# ── GET /should-show-paywall ────────────────────────────────────────────────


async def test_should_show_paywall_unauthenticated_returns_401(client):
    resp = await client.get(
        "/api/v1/payments/should-show-paywall", params={"trigger": "daily_review"}
    )
    assert resp.status_code == 401


async def test_should_show_paywall_invalid_trigger_returns_422(client, db_session):
    user = await _seed_user(db_session)
    # No trigger
    resp = await client.get(
        "/api/v1/payments/should-show-paywall", headers=_auth(user)
    )
    assert resp.status_code == 422
    # Empty trigger
    resp = await client.get(
        "/api/v1/payments/should-show-paywall",
        headers=_auth(user),
        params={"trigger": ""},
    )
    assert resp.status_code == 422


async def test_should_show_paywall_pro_user(client, db_session):
    pro = await _seed_user(db_session, plan="pro")
    resp = await client.get(
        "/api/v1/payments/should-show-paywall",
        headers=_auth(pro),
        params={"trigger": "daily_review"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"show": False, "attempts_until_next": 0}


async def test_should_show_paywall_free_within_grace(client, db_session):
    free = await _seed_user(db_session)
    # Seed a dismissal so grace is active.
    await client.post(
        "/api/v1/payments/paywall-dismiss",
        headers=_auth(free),
        json={"trigger": "daily_review"},
    )
    resp = await client.get(
        "/api/v1/payments/should-show-paywall",
        headers=_auth(free),
        params={"trigger": "daily_review", "attempts_since_dismiss": 1},
    )
    assert resp.status_code == 200
    assert resp.json() == {"show": False, "attempts_until_next": 2}


async def test_should_show_paywall_free_after_grace(client, db_session):
    free = await _seed_user(db_session)
    await client.post(
        "/api/v1/payments/paywall-dismiss",
        headers=_auth(free),
        json={"trigger": "daily_review"},
    )
    resp = await client.get(
        "/api/v1/payments/should-show-paywall",
        headers=_auth(free),
        params={"trigger": "daily_review", "attempts_since_dismiss": 3},
    )
    assert resp.status_code == 200
    assert resp.json() == {"show": True, "attempts_until_next": 3}
