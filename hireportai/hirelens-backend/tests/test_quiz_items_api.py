"""Integration tests for the quiz-items API (spec 6.2 §10.2).

Covers:
  GET  /api/v1/quiz-items/daily
  POST /api/v1/quiz-items/review
  GET  /api/v1/quiz-items/progress

Mirrors the test_study_api.py ASGI client + auth-via-google-mock pattern.
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
from app.models.quiz_item import QuizItem

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Client fixture (mirrors test_study_api.py) ───────────────────────────────


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
        "email": f"{uuid.uuid4()}@quiz-api-test.com",
        "name": "Quiz API Tester",
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


async def _seed_chain(db_session, *, archived_lesson=False, archived_deck=False, retired_quiz=False):
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"deck-{uuid.uuid4().hex[:6]}",
        title="API Test Deck",
        description="API tests",
        display_order=0,
        persona_visibility="both",
        tier="foundation",
        archived_at=datetime.now(timezone.utc) if archived_deck else None,
    )
    db_session.add(deck)
    await db_session.flush()

    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck.id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="API Test Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        archived_at=datetime.now(timezone.utc) if archived_lesson else None,
    )
    db_session.add(lesson)
    await db_session.flush()

    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson.id,
        question=f"Q-{uuid.uuid4().hex[:6]}?",
        answer="A.",
        question_type="free_text",
        difficulty="medium",
        display_order=0,
        version=1,
        retired_at=datetime.now(timezone.utc) if retired_quiz else None,
    )
    db_session.add(qi)
    await db_session.flush()
    return deck, lesson, qi


# ── Auth ─────────────────────────────────────────────────────────────────────


async def test_daily_endpoint_auth_required(client):
    resp = await client.get("/api/v1/quiz-items/daily")
    assert resp.status_code == 401


# ── GET /quiz-items/daily — sentinel daily_status (AC-6) ────────────────────


async def test_daily_endpoint_returns_sentinel_status(client, db_session):
    token, _ = await _sign_in(client)
    resp = await client.get(
        "/api/v1/quiz-items/daily",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["daily_status"]["cards_limit"] == -1
    assert body["daily_status"]["can_review"] is True
    assert isinstance(body["quiz_items"], list)


# ── POST /quiz-items/review — error paths ───────────────────────────────────


async def test_review_endpoint_404_unknown_quiz_item(client, db_session):
    token, _ = await _sign_in(client)
    body = {
        "quiz_item_id": str(uuid.uuid4()),
        "rating": 3,
        "session_id": str(uuid.uuid4()),
    }
    resp = await client.post(
        "/api/v1/quiz-items/review",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_review_endpoint_409_retired_no_progress(client, db_session):
    token, _ = await _sign_in(client)
    _, _, qi = await _seed_chain(db_session, retired_quiz=True)

    resp = await client.post(
        "/api/v1/quiz-items/review",
        json={
            "quiz_item_id": qi.id,
            "rating": 3,
            "session_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


async def test_review_endpoint_403_archived_lesson(client, db_session):
    token, _ = await _sign_in(client)
    _, _, qi = await _seed_chain(db_session, archived_lesson=True)

    resp = await client.post(
        "/api/v1/quiz-items/review",
        json={
            "quiz_item_id": qi.id,
            "rating": 3,
            "session_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── POST /quiz-items/review — happy path ────────────────────────────────────


async def test_review_endpoint_happy_path(client, db_session):
    token, _ = await _sign_in(client)
    _, lesson, qi = await _seed_chain(db_session)

    resp = await client.post(
        "/api/v1/quiz-items/review",
        json={
            "quiz_item_id": qi.id,
            "rating": 3,
            "session_id": str(uuid.uuid4()),
            "time_spent_ms": 1500,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["quiz_item_id"] == qi.id
    assert data["fsrs_state"] in ("learning", "review", "relearning")
    assert data["reps"] == 1
    assert data["lapses"] == 0
    assert data["scheduled_days"] >= 0


# ── GET /quiz-items/progress ────────────────────────────────────────────────


async def test_progress_endpoint_zero_when_empty(client, db_session):
    token, _ = await _sign_in(client)
    resp = await client.get(
        "/api/v1/quiz-items/progress",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_reviewed"] == 0
    assert data["total_reps"] == 0
    assert data["total_lapses"] == 0
    assert data["by_state"] == {"new": 0, "learning": 0, "review": 0, "relearning": 0}
