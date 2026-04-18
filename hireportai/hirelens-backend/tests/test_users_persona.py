"""Tests for PATCH /api/v1/users/me/persona and the updated /auth/me shape.

Covers the spec §Test Plan in
`docs/specs/phase-5/34-persona-picker-and-home.md`.

Users are seeded directly via the service layer and JWTs are issued
in-process — this sidesteps the per-IP registration cap enforced by
POST /api/v1/auth/google, which would otherwise 403 every test after
the second one (all tests share ``127.0.0.1`` under ``ASGITransport``).
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
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


async def _seed_user(db_session):
    """Insert a fresh user and return (user, bearer_token)."""
    email = f"{uuid.uuid4()}@example.com"
    user, _ = await get_or_create_user(
        google_id=f"g-{uuid.uuid4()}",
        email=email,
        name="Test User",
        avatar_url=None,
        db=db_session,
    )
    await db_session.commit()
    token = create_access_token({"sub": user.id, "email": user.email})
    return user, token


async def test_set_persona_valid_career_climber(client, db_session):
    """career_climber with no date/company persists; onboarding_completed flips."""
    user, token = await _seed_user(db_session)
    assert user.persona is None
    assert user.onboarding_completed is False

    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={"persona": "career_climber"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["persona"] == "career_climber"
    assert body["onboarding_completed"] is True
    assert body["interview_target_date"] is None
    assert body["interview_target_company"] is None


async def test_set_persona_valid_interview_prepper(client, db_session):
    """interview_prepper + date + company persists all three."""
    _, token = await _seed_user(db_session)
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={
            "persona": "interview_prepper",
            "interview_target_date": "2026-05-01",
            "interview_target_company": "Google",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["persona"] == "interview_prepper"
    assert body["interview_target_date"] == "2026-05-01"
    assert body["interview_target_company"] == "Google"
    assert body["onboarding_completed"] is True


async def test_set_persona_invalid_value(client, db_session):
    """Unknown persona string → HTTP 422."""
    _, token = await _seed_user(db_session)
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={"persona": "not_a_real_persona"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_interview_target_company_max_100_chars(client, db_session):
    """101-char company string → HTTP 422 with field error."""
    _, token = await _seed_user(db_session)
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={
            "persona": "interview_prepper",
            "interview_target_company": "x" * 101,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    locs = [
        ".".join(str(p) for p in err.get("loc", []))
        for err in resp.json()["detail"]
    ]
    assert any("interview_target_company" in loc for loc in locs)


async def test_auth_required_on_persona_patch(client):
    """Unauthenticated PATCH → HTTP 401."""
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={"persona": "career_climber"},
    )
    assert resp.status_code == 401


async def test_auth_me_includes_new_fields(client, db_session):
    """GET /auth/me returns interview_target_* and does not include legacy names."""
    _, token = await _seed_user(db_session)

    await client.patch(
        "/api/v1/users/me/persona",
        json={
            "persona": "interview_prepper",
            "interview_target_date": "2026-05-01",
            "interview_target_company": "Google",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["interview_target_date"] == "2026-05-01"
    assert body["interview_target_company"] == "Google"
    # Legacy field names must no longer appear.
    assert "target_date" not in body
    assert "target_company" not in body


async def test_legacy_onboarding_endpoint_returns_404(client, db_session):
    """PATCH /auth/onboarding no longer exists."""
    _, token = await _seed_user(db_session)
    resp = await client.patch(
        "/api/v1/auth/onboarding",
        json={"persona": "career_climber"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_legacy_persona_endpoint_returns_404(client, db_session):
    """PATCH /auth/persona no longer exists."""
    _, token = await _seed_user(db_session)
    resp = await client.patch(
        "/api/v1/auth/persona",
        json={"persona": "career_climber"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_empty_company_string_coerces_to_none(client, db_session):
    """Spec: trimmed empty string → None so the DB does not store whitespace."""
    _, token = await _seed_user(db_session)
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={
            "persona": "interview_prepper",
            "interview_target_company": "   ",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["interview_target_company"] is None


async def test_persona_switch_preserves_onboarding_flag(client, db_session):
    """Spec §API Contract: onboarding_completed is only flipped on first-time set."""
    _, token = await _seed_user(db_session)

    await client.patch(
        "/api/v1/users/me/persona",
        json={"persona": "career_climber"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Second call is a switch; onboarding_completed stays True either way,
    # but the handler must not regress it to False under any branch.
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={"persona": "team_lead"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["persona"] == "team_lead"
    assert resp.json()["onboarding_completed"] is True
