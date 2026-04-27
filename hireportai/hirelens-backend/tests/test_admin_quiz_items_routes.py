"""Admin quiz_item CRUD route tests (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §10.2 — `tests/test_admin_quiz_items_routes.py`.
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
from app.models.quiz_item import QuizItem
from app.models.quiz_item_progress import QuizItemProgress
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


async def _sign_in_admin(client, db_session) -> tuple[str, str]:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@admin-qi-test.com",
        "name": "Admin QI Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200
    data = resp.json()
    user_id = data["user"]["id"]
    await db_session.execute(
        sql_update(User).where(User.id == user_id).values(role="admin")
    )
    await db_session.flush()
    return data["access_token"], user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_deck(client, token) -> str:
    suffix = uuid.uuid4().hex[:8]
    resp = await client.post(
        "/api/v1/admin/decks",
        json={
            "slug": f"deck-qi-{suffix}",
            "title": f"Deck QI {suffix}",
            "description": "for quiz_item tests",
            "display_order": 0,
            "persona_visibility": "both",
            "tier": "foundation",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_lesson(client, token, deck_id) -> str:
    suffix = uuid.uuid4().hex[:8]
    resp = await client.post(
        f"/api/v1/admin/decks/{deck_id}/lessons",
        json={
            "slug": f"lesson-qi-{suffix}",
            "title": f"Lesson QI {suffix}",
            "concept_md": "## Concept\n\nSeed.",
            "production_md": "## Production\n\nSeed.",
            "examples_md": "## Examples\n\nSeed.",
            "display_order": 0,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_quiz_item_201(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson_id = await _create_lesson(client, token, deck_id)
    resp = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items",
        json={
            "question": "What is X?",
            "answer": "X is a thing.",
            "question_type": "free_text",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["lesson_id"] == lesson_id
    assert body["version"] == 1
    assert body["retired_at"] is None
    assert body["superseded_by_id"] is None


async def test_create_quiz_item_409_archived_lesson(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson_id = await _create_lesson(client, token, deck_id)
    archive = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/archive", headers=_auth(token)
    )
    assert archive.status_code == 200
    resp = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items",
        json={
            "question": "Q?",
            "answer": "A.",
            "question_type": "free_text",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 409


async def test_update_quiz_item_substantive_creates_replacement(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson_id = await _create_lesson(client, token, deck_id)
    create = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items",
        json={
            "question": "What is the original question that's reasonably long?",
            "answer": "Original answer that's also long enough to differentiate.",
            "question_type": "free_text",
        },
        headers=_auth(token),
    )
    assert create.status_code == 201
    old_id = create.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/admin/quiz-items/{old_id}",
        json={
            "edit_classification": "substantive",
            "question": "Entirely different question rewritten from scratch — wholly novel content.",
        },
        headers=_auth(token),
    )
    assert patch_resp.status_code == 200, patch_resp.text
    new_body = patch_resp.json()
    assert new_body["id"] != old_id
    assert new_body["version"] == 2
    assert new_body["lesson_id"] == lesson_id
    assert new_body["retired_at"] is None

    # Old row in DB should be retired with a forward link to new.
    result = await db_session.execute(select(QuizItem).where(QuizItem.id == old_id))
    old = result.scalar_one()
    assert old.retired_at is not None
    assert old.superseded_by_id == new_body["id"]


async def test_update_quiz_item_minor_in_place(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson_id = await _create_lesson(client, token, deck_id)
    create = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items",
        json={
            "question": "What is the answer?",
            "answer": "42",
            "question_type": "free_text",
            "difficulty": "easy",
        },
        headers=_auth(token),
    )
    assert create.status_code == 201
    qi_id = create.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/admin/quiz-items/{qi_id}",
        json={"edit_classification": "minor", "difficulty": "hard"},
        headers=_auth(token),
    )
    assert patch_resp.status_code == 200, patch_resp.text
    body = patch_resp.json()
    assert body["id"] == qi_id  # same row, no replacement
    assert body["version"] == 1  # version unchanged on minor
    assert body["difficulty"] == "hard"


async def test_retire_quiz_item_idempotent(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson_id = await _create_lesson(client, token, deck_id)
    create = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items",
        json={"question": "Q?", "answer": "A.", "question_type": "free_text"},
        headers=_auth(token),
    )
    assert create.status_code == 201
    qi_id = create.json()["id"]

    first = await client.post(
        f"/api/v1/admin/quiz-items/{qi_id}/retire",
        json={"superseded_by_id": None},
        headers=_auth(token),
    )
    assert first.status_code == 200
    assert first.json()["retired_at"] is not None
    retired_at = first.json()["retired_at"]

    second = await client.post(
        f"/api/v1/admin/quiz-items/{qi_id}/retire",
        json={"superseded_by_id": None},
        headers=_auth(token),
    )
    assert second.status_code == 200
    assert second.json()["retired_at"] == retired_at


async def test_retire_quiz_item_preserves_progress_rows(client, db_session):
    token, admin_id = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson_id = await _create_lesson(client, token, deck_id)
    create = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items",
        json={"question": "Q?", "answer": "A.", "question_type": "free_text"},
        headers=_auth(token),
    )
    assert create.status_code == 201
    qi_id = create.json()["id"]

    progress = QuizItemProgress(user_id=admin_id, quiz_item_id=qi_id)
    db_session.add(progress)
    await db_session.flush()

    retire_resp = await client.post(
        f"/api/v1/admin/quiz-items/{qi_id}/retire",
        json={"superseded_by_id": None},
        headers=_auth(token),
    )
    assert retire_resp.status_code == 200

    result = await db_session.execute(
        select(QuizItemProgress).where(
            QuizItemProgress.user_id == admin_id,
            QuizItemProgress.quiz_item_id == qi_id,
        )
    )
    row = result.scalar_one_or_none()
    assert row is not None  # progress row survives quiz_item retirement


async def test_list_admin_quiz_items_status_filter(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson_id = await _create_lesson(client, token, deck_id)
    active = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items",
        json={"question": "Active?", "answer": "Y.", "question_type": "free_text"},
        headers=_auth(token),
    )
    retired = await client.post(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items",
        json={"question": "To retire?", "answer": "Y.", "question_type": "free_text"},
        headers=_auth(token),
    )
    retired_id = retired.json()["id"]
    await client.post(
        f"/api/v1/admin/quiz-items/{retired_id}/retire",
        json={"superseded_by_id": None},
        headers=_auth(token),
    )

    list_active = await client.get(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items?status=active",
        headers=_auth(token),
    )
    active_ids = {qi["id"] for qi in list_active.json()}
    assert active.json()["id"] in active_ids
    assert retired_id not in active_ids

    list_retired = await client.get(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items?status=retired",
        headers=_auth(token),
    )
    retired_ids = {qi["id"] for qi in list_retired.json()}
    assert retired_id in retired_ids


async def test_list_admin_quiz_items_rejects_invalid_status(client, db_session):
    token, _ = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson_id = await _create_lesson(client, token, deck_id)
    resp = await client.get(
        f"/api/v1/admin/lessons/{lesson_id}/quiz-items?status=archived",
        headers=_auth(token),
    )
    assert resp.status_code == 422
