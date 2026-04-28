"""Integration tests for `POST /api/v1/lessons/{lesson_id}/view-event`.

Spec: docs/specs/phase-6/00-analytics-tables.md §6.3 + §10.4 + AC-4.

Mirrors the test_quiz_items_api.py ASGI client + auth-via-google-mock pattern.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

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
        "email": f"{uuid.uuid4()}@lesson-view-test.com",
        "name": "Lesson View Tester",
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


async def _seed_chain(db_session):
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"deck-{uuid.uuid4().hex[:6]}",
        title="LV Deck",
        description="lv",
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
        title="LV Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
    )
    db_session.add(lesson)
    await db_session.flush()
    return deck, lesson


# ── Auth gate ─────────────────────────────────────────────────────────────────


async def test_post_lesson_view_event_401_unauthenticated(client, db_session):
    deck, lesson = await _seed_chain(db_session)
    body = {"deck_id": deck.id, "version": 1, "session_id": str(uuid.uuid4())}
    resp = await client.post(
        f"/api/v1/lessons/{lesson.id}/view-event",
        json=body,
    )
    assert resp.status_code == 401


# ── Happy path (AC-4) ────────────────────────────────────────────────────────


async def test_post_lesson_view_event_204(client, db_session):
    token, user_id = await _sign_in(client)
    deck, lesson = await _seed_chain(db_session)

    body = {
        "deck_id": deck.id,
        "version": 1,
        "session_id": str(uuid.uuid4()),
    }
    resp = await client.post(
        f"/api/v1/lessons/{lesson.id}/view-event",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204, resp.text
    assert resp.content in (b"", b"null")  # 204 — no body.

    rows = (
        await db_session.execute(
            text("SELECT user_id, lesson_id, deck_id, version, session_id "
                 "FROM lesson_view_events WHERE lesson_id = :lid"),
            {"lid": lesson.id},
        )
    ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == user_id
    assert row.lesson_id == lesson.id
    assert row.deck_id == deck.id
    assert row.version == 1
    assert row.session_id == body["session_id"]


# ── 404 — unknown lesson ──────────────────────────────────────────────────────


async def test_post_lesson_view_event_404_unknown_lesson(client, db_session):
    token, _ = await _sign_in(client)
    body = {
        "deck_id": str(uuid.uuid4()),
        "version": 1,
        "session_id": str(uuid.uuid4()),
    }
    resp = await client.post(
        f"/api/v1/lessons/{uuid.uuid4()}/view-event",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── 422 — defensive deck_id mismatch (§6.3) ──────────────────────────────────


async def test_post_lesson_view_event_422_deck_id_mismatch(client, db_session):
    token, _ = await _sign_in(client)
    _, lesson = await _seed_chain(db_session)
    body = {
        "deck_id": str(uuid.uuid4()),  # not the lesson's deck.
        "version": 1,
        "session_id": str(uuid.uuid4()),
    }
    resp = await client.post(
        f"/api/v1/lessons/{lesson.id}/view-event",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
