"""Lesson service DB-query tests (slice 6.4b — body swap of `lesson_service.py`).

Spec: docs/specs/phase-6/04-admin-authoring.md §10.2 +
       docs/specs/phase-6/03-lesson-ux.md §10.1.

Replaces `tests/test_lesson_fixtures_routes.py` (slice 6.3 era). Seeds
the DB directly because routes are no longer fixture-backed; the four
`lesson_service` functions now hit Postgres with `selectinload` per
D-15.
"""
from __future__ import annotations

import os
import uuid
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
        "email": f"{uuid.uuid4()}@lesson-svc-test.com",
        "name": "Lesson Svc Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _seed_deck(db_session, *, archived: bool = False) -> Deck:
    suffix = uuid.uuid4().hex[:8]
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"db-test-deck-{suffix}",
        title=f"DB Test Deck {suffix}",
        description="Seeded for DB-query tests.",
        display_order=0,
        persona_visibility="both",
        tier="foundation",
    )
    db_session.add(deck)
    await db_session.flush()
    if archived:
        from sqlalchemy import func as sql_func
        deck.archived_at = sql_func.now()
        await db_session.flush()
        await db_session.refresh(deck)
    return deck


async def _seed_lesson(
    db_session,
    deck: Deck,
    *,
    slug: str | None = None,
    display_order: int = 0,
    published: bool = True,
    archived: bool = False,
) -> Lesson:
    suffix = uuid.uuid4().hex[:8]
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck.id,
        slug=slug or f"db-test-lesson-{suffix}",
        title=f"DB Test Lesson {suffix}",
        concept_md="## Concept\n\nSeeded.",
        production_md="## Production\n\nSeeded.",
        examples_md="## Examples\n\nSeeded.",
        display_order=display_order,
        version=1,
        version_type="initial",
    )
    db_session.add(lesson)
    await db_session.flush()
    from sqlalchemy import func as sql_func
    if published:
        lesson.published_at = sql_func.now()
    if archived:
        lesson.archived_at = sql_func.now()
    await db_session.flush()
    await db_session.refresh(lesson)
    return lesson


async def _seed_quiz_item(
    db_session,
    lesson: Lesson,
    *,
    display_order: int = 0,
    retired: bool = False,
) -> QuizItem:
    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson.id,
        question="What is the answer?",
        answer="42",
        question_type="free_text",
        difficulty="medium",
        display_order=display_order,
        version=1,
    )
    db_session.add(qi)
    await db_session.flush()
    if retired:
        from sqlalchemy import func as sql_func
        qi.retired_at = sql_func.now()
        await db_session.flush()
        await db_session.refresh(qi)
    return qi


# ── /api/v1/lessons/{id} ─────────────────────────────────────────────────────


async def test_get_lesson_returns_db_lesson_with_quizzes(client, db_session):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck)
    await _seed_quiz_item(db_session, lesson, display_order=0)
    await _seed_quiz_item(db_session, lesson, display_order=1)
    await _seed_quiz_item(db_session, lesson, display_order=2)

    resp = await client.get(
        f"/api/v1/lessons/{lesson.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lesson"]["id"] == lesson.id
    assert body["deck_id"] == deck.id
    assert body["deck_slug"] == deck.slug
    assert body["deck_title"] == deck.title
    assert len(body["quiz_items"]) == 3
    assert [qi["display_order"] for qi in body["quiz_items"]] == [0, 1, 2]


async def test_get_lesson_excludes_unpublished(client, db_session):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck, published=False)
    resp = await client.get(
        f"/api/v1/lessons/{lesson.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_lesson_excludes_archived(client, db_session):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck, archived=True)
    resp = await client.get(
        f"/api/v1/lessons/{lesson.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_lesson_filters_retired_quiz_items(client, db_session):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck)
    await _seed_quiz_item(db_session, lesson, display_order=0)
    await _seed_quiz_item(db_session, lesson, display_order=1)
    await _seed_quiz_item(db_session, lesson, display_order=2, retired=True)

    resp = await client.get(
        f"/api/v1/lessons/{lesson.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["quiz_items"]) == 2
    assert all(qi["display_order"] in (0, 1) for qi in body["quiz_items"])


async def test_get_lesson_404_unknown_id(client):
    token = await _sign_in(client)
    resp = await client.get(
        f"/api/v1/lessons/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_lesson_auth_required(client):
    resp = await client.get(f"/api/v1/lessons/{uuid.uuid4()}")
    assert resp.status_code == 401


# ── /api/v1/decks/{id} ───────────────────────────────────────────────────────


async def test_get_deck_excludes_archived(client, db_session):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session, archived=True)
    resp = await client.get(
        f"/api/v1/decks/{deck.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_deck_404_unknown_id(client):
    token = await _sign_in(client)
    resp = await client.get(
        f"/api/v1/decks/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_deck_returns_seeded(client, db_session):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session)
    resp = await client.get(
        f"/api/v1/decks/{deck.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == deck.id
    assert body["slug"] == deck.slug


# ── /api/v1/decks/{id}/lessons ───────────────────────────────────────────────


async def test_list_deck_lessons_orders_by_display_order_then_created_at(
    client, db_session
):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session)
    second = await _seed_lesson(db_session, deck, display_order=1)
    first = await _seed_lesson(db_session, deck, display_order=0)
    resp = await client.get(
        f"/api/v1/decks/{deck.id}/lessons",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [l["id"] for l in body["lessons"]] == [first.id, second.id]


async def test_list_deck_lessons_filters_unpublished_for_user_facing_route(
    client, db_session
):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session)
    pub = await _seed_lesson(db_session, deck, display_order=0, published=True)
    await _seed_lesson(db_session, deck, display_order=1, published=False)
    resp = await client.get(
        f"/api/v1/decks/{deck.id}/lessons",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [l["id"] for l in body["lessons"]] == [pub.id]


async def test_get_deck_lessons_bundle_404_unknown_deck(client):
    token = await _sign_in(client)
    resp = await client.get(
        f"/api/v1/decks/{uuid.uuid4()}/lessons",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_deck_lessons_bundle_empty_lessons(client, db_session):
    token = await _sign_in(client)
    deck = await _seed_deck(db_session)
    resp = await client.get(
        f"/api/v1/decks/{deck.id}/lessons",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deck"]["id"] == deck.id
    assert body["lessons"] == []


# ── Fixture-module retirement (AC-6) ─────────────────────────────────────────


async def test_lesson_fixtures_module_deleted():
    """`app/data/lesson_fixtures.py` no longer exists; no remaining imports."""
    repo_app = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"
    )
    fixtures_path = os.path.join(repo_app, "data", "lesson_fixtures.py")
    assert not os.path.exists(fixtures_path), (
        f"lesson_fixtures.py still on disk at {fixtures_path}"
    )

    init_path = os.path.join(repo_app, "data", "__init__.py")
    assert not os.path.exists(init_path), (
        f"app/data/__init__.py still on disk at {init_path}"
    )

    # No remaining `lesson_fixtures` imports under app/.
    for root, _dirs, files in os.walk(repo_app):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            full = os.path.join(root, fname)
            with open(full, "r", encoding="utf-8") as fh:
                contents = fh.read()
            assert "lesson_fixtures" not in contents, (
                f"stale `lesson_fixtures` reference in {full}"
            )
