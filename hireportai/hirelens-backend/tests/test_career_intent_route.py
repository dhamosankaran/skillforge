"""Tests for ``POST/GET/DELETE /api/v1/users/me/career-intent`` (B-125a).

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §6.2 + §11
AC-8..AC-12. Focused on auth, persona guard, validation, captured-vs-
updated telemetry discrimination, and 204/404 happy paths.
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
from app.schemas.career_intent import _current_quarter_tuple
from app.services.user_service import get_or_create_user

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


def _future_quarter() -> str:
    year, q = _current_quarter_tuple()
    if q == 4:
        return f"{year + 1}-Q1"
    return f"{year}-Q{q + 1}"


async def _seed_user(db_session, *, persona: str | None = "career_climber"):
    user, _ = await get_or_create_user(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Test User",
        avatar_url=None,
        db=db_session,
    )
    user.persona = persona
    if persona is not None:
        user.onboarding_completed = True
    await db_session.commit()
    token = create_access_token({"sub": user.id, "email": user.email})
    return user, token


# ── POST /career-intent ─────────────────────────────────────────────────────


async def test_post_career_intent_requires_auth(client):
    resp = await client.post(
        "/api/v1/users/me/career-intent",
        json={"target_role": "staff", "target_quarter": _future_quarter()},
    )
    assert resp.status_code == 401


async def test_post_career_intent_rejects_non_cc_persona(client, db_session):
    _, token = await _seed_user(db_session, persona="interview_prepper")
    resp = await client.post(
        "/api/v1/users/me/career-intent",
        json={"target_role": "staff", "target_quarter": _future_quarter()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    assert "career_climber" in resp.json()["detail"]


async def test_post_career_intent_rejects_invalid_role(client, db_session):
    _, token = await _seed_user(db_session)
    resp = await client.post(
        "/api/v1/users/me/career-intent",
        json={"target_role": "vp", "target_quarter": _future_quarter()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_post_career_intent_rejects_past_quarter(client, db_session):
    _, token = await _seed_user(db_session)
    resp = await client.post(
        "/api/v1/users/me/career-intent",
        json={"target_role": "staff", "target_quarter": "2020-Q1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_post_career_intent_first_capture_fires_captured_event(
    client, db_session
):
    user, token = await _seed_user(db_session)
    captured: list[tuple[str, str, dict]] = []

    with patch(
        "app.api.v1.routes.career_intent.analytics_track",
        side_effect=lambda uid, evt, props: captured.append((uid, evt, props)),
    ):
        resp = await client.post(
            "/api/v1/users/me/career-intent",
            json={
                "target_role": "staff",
                "target_quarter": _future_quarter(),
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-Capture-Source": "persona_picker",
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["target_role"] == "staff"
    assert body["user_id"] == user.id
    assert body["superseded_at"] is None
    assert any(evt == "career_intent_captured" for _, evt, _ in captured)
    assert not any(evt == "career_intent_updated" for _, evt, _ in captured)
    captured_props = next(props for _, evt, props in captured if evt == "career_intent_captured")
    assert captured_props["source"] == "persona_picker"


async def test_post_career_intent_second_capture_fires_updated_event(
    client, db_session
):
    user, token = await _seed_user(db_session)
    quarter = _future_quarter()

    # First write — should produce _captured.
    await client.post(
        "/api/v1/users/me/career-intent",
        json={"target_role": "staff", "target_quarter": quarter},
        headers={"Authorization": f"Bearer {token}"},
    )

    captured: list[tuple[str, str, dict]] = []
    with patch(
        "app.api.v1.routes.career_intent.analytics_track",
        side_effect=lambda uid, evt, props: captured.append((uid, evt, props)),
    ):
        resp = await client.post(
            "/api/v1/users/me/career-intent",
            json={"target_role": "principal", "target_quarter": quarter},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201
    updated_props = next(p for _, e, p in captured if e == "career_intent_updated")
    assert updated_props["from_role"] == "staff"
    assert updated_props["to_role"] == "principal"


# ── GET /career-intent ──────────────────────────────────────────────────────


async def test_get_career_intent_returns_404_when_no_current(client, db_session):
    _, token = await _seed_user(db_session)
    resp = await client.get(
        "/api/v1/users/me/career-intent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_career_intent_returns_current_row(client, db_session):
    _, token = await _seed_user(db_session)
    quarter = _future_quarter()
    await client.post(
        "/api/v1/users/me/career-intent",
        json={"target_role": "em", "target_quarter": quarter},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/users/me/career-intent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_role"] == "em"
    assert body["target_quarter"] == quarter
    assert body["superseded_at"] is None


# ── DELETE /career-intent ───────────────────────────────────────────────────


async def test_delete_career_intent_clears_current_row(client, db_session):
    _, token = await _seed_user(db_session)
    quarter = _future_quarter()
    await client.post(
        "/api/v1/users/me/career-intent",
        json={"target_role": "director", "target_quarter": quarter},
        headers={"Authorization": f"Bearer {token}"},
    )

    captured: list[tuple[str, str, dict]] = []
    with patch(
        "app.api.v1.routes.career_intent.analytics_track",
        side_effect=lambda uid, evt, props: captured.append((uid, evt, props)),
    ):
        resp = await client.delete(
            "/api/v1/users/me/career-intent",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 204
    # GET now 404
    resp = await client.get(
        "/api/v1/users/me/career-intent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    cleared_props = next(
        p for _, e, p in captured if e == "career_intent_updated"
    )
    assert cleared_props["from_role"] == "director"
    assert cleared_props["to_role"] is None


async def test_delete_career_intent_no_op_when_nothing_to_clear(
    client, db_session
):
    _, token = await _seed_user(db_session)
    resp = await client.delete(
        "/api/v1/users/me/career-intent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
