"""Integration tests for ``POST /api/v1/lessons/{lesson_id}/thumbs``.

Spec: docs/specs/phase-6/12-quality-signals.md §6.4 + §11
AC-5..AC-8 + §12 D-7 / D-10 / D-11.

Mirrors the ``test_lesson_view_route.py`` ASGI client + auth-via-google
pattern.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.deck import Deck
from app.models.lesson import Lesson

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
        "email": f"{uuid.uuid4()}@thumbs-test.com",
        "name": "Thumbs Tester",
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


async def _seed_chain(
    db_session, *, archived: bool = False, published: bool = True
) -> tuple[Deck, Lesson]:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"deck-{uuid.uuid4().hex[:6]}",
        title="Thumb Deck",
        description="seed",
        display_order=0,
        persona_visibility="both",
        tier="foundation",
    )
    db_session.add(deck)
    await db_session.flush()
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck.id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Thumb Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=(
            datetime.now(timezone.utc) if published else None
        ),
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(lesson)
    await db_session.flush()
    return deck, lesson


# ── AC-5: unauthenticated → 401 ─────────────────────────────────────────────


async def test_thumbs_post_401_unauthenticated(client, db_session):
    _, lesson = await _seed_chain(db_session)
    resp = await client.post(
        f"/api/v1/lessons/{lesson.id}/thumbs", json={"score": 1}
    )
    assert resp.status_code == 401


# ── AC-7: happy path 200 + ThumbsResponse ──────────────────────────────────


async def test_thumbs_post_200_authed_visible_lesson(client, db_session):
    token, _ = await _sign_in(client)
    _, lesson = await _seed_chain(db_session)

    resp = await client.post(
        f"/api/v1/lessons/{lesson.id}/thumbs",
        json={"score": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["accepted"] is True
    assert payload["score"] == 1
    assert payload["aggregate_score"] == 1.0
    assert payload["aggregate_count"] == 1


# ── AC-8: validator rejects values outside {-1, +1} ────────────────────────


@pytest.mark.parametrize("invalid_score", [0, 2, -2, 5])
async def test_thumbs_post_422_on_invalid_score(client, db_session, invalid_score):
    token, _ = await _sign_in(client)
    _, lesson = await _seed_chain(db_session)

    resp = await client.post(
        f"/api/v1/lessons/{lesson.id}/thumbs",
        json={"score": invalid_score},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ── AC-6: archived lesson → 404 ────────────────────────────────────────────


async def test_thumbs_post_404_on_archived_lesson(client, db_session):
    token, _ = await _sign_in(client)
    _, lesson = await _seed_chain(db_session, archived=True)

    resp = await client.post(
        f"/api/v1/lessons/{lesson.id}/thumbs",
        json={"score": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_thumbs_post_404_on_unknown_lesson(client, db_session):
    token, _ = await _sign_in(client)
    resp = await client.post(
        "/api/v1/lessons/missing-id/thumbs",
        json={"score": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
