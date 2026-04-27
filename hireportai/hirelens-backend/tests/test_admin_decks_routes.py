"""Admin deck CRUD route tests (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §10.2 — `tests/test_admin_decks_routes.py`.
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


async def _sign_in(client, db_session, role: str = "user") -> tuple[str, str]:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@admin-decks-test.com",
        "name": "Admin Decks Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    if role == "admin":
        await db_session.execute(
            sql_update(User).where(User.id == data["user"]["id"]).values(role="admin")
        )
        await db_session.flush()
    return data["access_token"], data["user"]["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _new_deck_payload(slug: str | None = None) -> dict:
    suffix = uuid.uuid4().hex[:8]
    return {
        "slug": slug or f"deck-test-{suffix}",
        "title": f"Test Deck {suffix}",
        "description": "Authoring fixture.",
        "display_order": 0,
        "persona_visibility": "both",
        "tier": "premium",
    }


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_deck_201_response_shape(client, db_session):
    token, _ = await _sign_in(client, db_session, role="admin")
    payload = _new_deck_payload()
    resp = await client.post("/api/v1/admin/decks", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["slug"] == payload["slug"]
    assert body["title"] == payload["title"]
    assert body["persona_visibility"] == "both"
    assert body["tier"] == "premium"
    assert body["archived_at"] is None


async def test_create_deck_409_slug_conflict(client, db_session):
    token, _ = await _sign_in(client, db_session, role="admin")
    payload = _new_deck_payload()
    first = await client.post("/api/v1/admin/decks", json=payload, headers=_auth(token))
    assert first.status_code == 201
    dup = await client.post("/api/v1/admin/decks", json=payload, headers=_auth(token))
    assert dup.status_code == 409


async def test_create_deck_403_non_admin(client, db_session):
    token, _ = await _sign_in(client, db_session, role="user")
    resp = await client.post(
        "/api/v1/admin/decks", json=_new_deck_payload(), headers=_auth(token)
    )
    assert resp.status_code == 403


async def test_create_deck_401_unauthenticated(client):
    resp = await client.post("/api/v1/admin/decks", json=_new_deck_payload())
    assert resp.status_code == 401


async def test_update_deck_200_partial_payload(client, db_session):
    token, _ = await _sign_in(client, db_session, role="admin")
    create = await client.post(
        "/api/v1/admin/decks", json=_new_deck_payload(), headers=_auth(token)
    )
    deck_id = create.json()["id"]
    original_slug = create.json()["slug"]

    resp = await client.patch(
        f"/api/v1/admin/decks/{deck_id}",
        json={"title": "Renamed Title Only"},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Renamed Title Only"
    assert body["slug"] == original_slug


async def test_archive_deck_idempotent(client, db_session):
    token, _ = await _sign_in(client, db_session, role="admin")
    create = await client.post(
        "/api/v1/admin/decks", json=_new_deck_payload(), headers=_auth(token)
    )
    deck_id = create.json()["id"]

    first = await client.post(
        f"/api/v1/admin/decks/{deck_id}/archive", headers=_auth(token)
    )
    assert first.status_code == 200
    assert first.json()["archived_at"] is not None
    archived_at = first.json()["archived_at"]

    second = await client.post(
        f"/api/v1/admin/decks/{deck_id}/archive", headers=_auth(token)
    )
    assert second.status_code == 200
    assert second.json()["archived_at"] == archived_at


async def test_list_decks_status_filter(client, db_session):
    token, _ = await _sign_in(client, db_session, role="admin")
    active = await client.post(
        "/api/v1/admin/decks", json=_new_deck_payload(), headers=_auth(token)
    )
    archived_resp = await client.post(
        "/api/v1/admin/decks", json=_new_deck_payload(), headers=_auth(token)
    )
    archived_id = archived_resp.json()["id"]
    await client.post(
        f"/api/v1/admin/decks/{archived_id}/archive", headers=_auth(token)
    )

    list_active = await client.get(
        "/api/v1/admin/decks?status=active", headers=_auth(token)
    )
    active_ids = {d["id"] for d in list_active.json()}
    assert active.json()["id"] in active_ids
    assert archived_id not in active_ids

    list_archived = await client.get(
        "/api/v1/admin/decks?status=archived", headers=_auth(token)
    )
    archived_ids = {d["id"] for d in list_archived.json()}
    assert archived_id in archived_ids
    assert active.json()["id"] not in archived_ids

    list_all = await client.get("/api/v1/admin/decks?status=all", headers=_auth(token))
    all_ids = {d["id"] for d in list_all.json()}
    assert {active.json()["id"], archived_id} <= all_ids


async def test_list_decks_rejects_invalid_status(client, db_session):
    token, _ = await _sign_in(client, db_session, role="admin")
    resp = await client.get(
        "/api/v1/admin/decks?status=garbage", headers=_auth(token)
    )
    assert resp.status_code == 422


async def test_admin_audit_log_row_per_request(client, db_session):
    token, admin_id = await _sign_in(client, db_session, role="admin")
    before = await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.admin_id == admin_id)
    )
    baseline = len(before.scalars().all())

    resp = await client.post(
        "/api/v1/admin/decks", json=_new_deck_payload(), headers=_auth(token)
    )
    assert resp.status_code == 201

    after = await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.admin_id == admin_id)
    )
    rows = after.scalars().all()
    assert len(rows) == baseline + 1
    assert rows[-1].route == "/api/v1/admin/decks"
    assert rows[-1].method == "POST"
