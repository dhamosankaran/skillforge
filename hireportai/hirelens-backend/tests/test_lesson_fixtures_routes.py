"""Integration tests for the lesson + deck API routes (slice 6.3).

Spec: docs/specs/phase-6/03-lesson-ux.md §10.1.

Covers:
  GET /api/v1/lessons/{lesson_id}
  GET /api/v1/decks/{deck_id}
  GET /api/v1/decks/{deck_id}/lessons

Mirrors test_quiz_items_api.py's ASGI-client + google-mock auth pattern.
Routes return fixture data (no DB read in slice 6.3) so the tests do
not seed the database — they assert against fixtures from
`app/data/lesson_fixtures.py`.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.data import lesson_fixtures
from app.db.session import get_db
from app.main import app

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


async def _sign_in(client) -> str:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@lesson-api-test.com",
        "name": "Lesson API Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ── /api/v1/lessons/{id} ─────────────────────────────────────────────────────


async def test_get_lesson_auth_required(client):
    resp = await client.get("/api/v1/lessons/lesson-fixture-attention-mechanism")
    assert resp.status_code == 401


async def test_get_lesson_404_unknown_id(client):
    token = await _sign_in(client)
    resp = await client.get(
        f"/api/v1/lessons/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_lesson_returns_fixture_with_quizzes(client):
    token = await _sign_in(client)
    resp = await client.get(
        "/api/v1/lessons/lesson-fixture-attention-mechanism",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lesson"]["id"] == "lesson-fixture-attention-mechanism"
    assert body["lesson"]["title"] == "The Attention Mechanism"
    assert body["deck_id"] == "deck-fixture-transformer-llm-internals"
    assert body["deck_slug"] == "transformer-llm-internals"
    assert body["deck_title"] == "Transformer LLM Internals"
    quiz_items = body["quiz_items"]
    assert len(quiz_items) == 3
    # display_order ascending
    assert [qi["display_order"] for qi in quiz_items] == [0, 1, 2]
    # spans all three question_type values
    assert {qi["question_type"] for qi in quiz_items} == {
        "free_text",
        "mcq",
        "code_completion",
    }


# ── /api/v1/decks/{id} ───────────────────────────────────────────────────────


async def test_get_deck_404_unknown_id(client):
    token = await _sign_in(client)
    resp = await client.get(
        f"/api/v1/decks/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_deck_returns_fixture(client):
    token = await _sign_in(client)
    resp = await client.get(
        "/api/v1/decks/deck-fixture-transformer-llm-internals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == "deck-fixture-transformer-llm-internals"
    assert body["slug"] == "transformer-llm-internals"
    assert body["tier"] == "foundation"
    assert body["persona_visibility"] == "both"


# ── /api/v1/decks/{id}/lessons ───────────────────────────────────────────────


async def test_list_deck_lessons_returns_ordered(client):
    token = await _sign_in(client)
    resp = await client.get(
        "/api/v1/decks/deck-fixture-transformer-llm-internals/lessons",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deck"]["id"] == "deck-fixture-transformer-llm-internals"
    lessons = body["lessons"]
    assert len(lessons) == 2
    assert [lsn["display_order"] for lsn in lessons] == [0, 1]
    assert lessons[0]["slug"] == "attention-mechanism"
    assert lessons[1]["slug"] == "tokenization-byte-pair-encoding"


async def test_list_deck_lessons_empty_deck(client, monkeypatch):
    """A deck that exists with zero lessons returns 200 + empty list."""
    # Inject a synthetic empty deck via the fixture loader's private
    # dict, then restore on cleanup.
    from app.schemas.deck import DeckResponse
    from datetime import datetime, timezone

    empty_deck_id = "deck-fixture-empty-test-only"
    lesson_fixtures._DECKS[empty_deck_id] = DeckResponse(
        id=empty_deck_id,
        slug="empty-test-only",
        title="Empty Test Deck",
        description="No lessons.",
        display_order=99,
        icon=None,
        persona_visibility="both",
        tier="foundation",
        created_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        archived_at=None,
    )
    try:
        token = await _sign_in(client)
        resp = await client.get(
            f"/api/v1/decks/{empty_deck_id}/lessons",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["deck"]["id"] == empty_deck_id
        assert body["lessons"] == []
    finally:
        lesson_fixtures._DECKS.pop(empty_deck_id, None)
