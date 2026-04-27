"""Admin lesson CRUD route tests (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §10.2 — `tests/test_admin_lessons_routes.py`.
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
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
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


async def _sign_in_admin(client, db_session) -> str:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@admin-lessons-test.com",
        "name": "Admin Lessons Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200
    data = resp.json()
    await db_session.execute(
        sql_update(User).where(User.id == data["user"]["id"]).values(role="admin")
    )
    await db_session.flush()
    return data["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _deck_payload() -> dict:
    suffix = uuid.uuid4().hex[:8]
    return {
        "slug": f"deck-l-{suffix}",
        "title": f"Deck {suffix}",
        "description": "for lesson tests",
        "display_order": 0,
        "persona_visibility": "both",
        "tier": "foundation",
    }


def _lesson_payload(slug: str | None = None) -> dict:
    suffix = uuid.uuid4().hex[:8]
    return {
        "slug": slug or f"lesson-{suffix}",
        "title": f"Lesson {suffix}",
        "concept_md": "## Concept\n\nThis is a concept that's reasonably long so the threshold logic has substance to compare against.",
        "production_md": "## Production\n\nProduction notes — also long enough to differentiate from substantive edits.",
        "examples_md": "## Examples\n\nExample one. Example two. Example three.",
        "display_order": 0,
    }


async def _create_deck(client, token, *, payload=None) -> str:
    resp = await client.post(
        "/api/v1/admin/decks", json=payload or _deck_payload(), headers=_auth(token)
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_lesson(client, token, deck_id, *, payload=None) -> dict:
    resp = await client.post(
        f"/api/v1/admin/decks/{deck_id}/lessons",
        json=payload or _lesson_payload(),
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_lesson_201_within_deck(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson = await _create_lesson(client, token, deck_id)
    assert lesson["deck_id"] == deck_id
    assert lesson["version"] == 1
    assert lesson["version_type"] == "initial"
    assert lesson["published_at"] is None


async def test_create_lesson_404_unknown_deck(client, db_session):
    token = await _sign_in_admin(client, db_session)
    resp = await client.post(
        f"/api/v1/admin/decks/{uuid.uuid4()}/lessons",
        json=_lesson_payload(),
        headers=_auth(token),
    )
    assert resp.status_code == 404


async def test_create_lesson_409_composite_slug_conflict(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    payload = _lesson_payload(slug="duplicate-slug")
    first = await _create_lesson(client, token, deck_id, payload=payload)
    assert first["slug"] == "duplicate-slug"
    dup = await client.post(
        f"/api/v1/admin/decks/{deck_id}/lessons",
        json=payload,
        headers=_auth(token),
    )
    assert dup.status_code == 409


async def test_update_lesson_minor_no_cascade(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson = await _create_lesson(client, token, deck_id)
    # Seed a quiz_item under it.
    await client.post(
        f"/api/v1/admin/lessons/{lesson['id']}/quiz-items",
        json={"question": "Q?", "answer": "A.", "question_type": "free_text"},
        headers=_auth(token),
    )

    resp = await client.patch(
        f"/api/v1/admin/lessons/{lesson['id']}",
        json={"edit_classification": "minor", "title": "Renamed Lesson Title"},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lesson"]["title"] == "Renamed Lesson Title"
    assert body["version_type_applied"] == "minor"
    assert body["quiz_items_retired_count"] == 0
    assert body["quiz_items_retired_ids"] == []
    assert body["lesson"]["version_type"] == "minor_edit"
    assert body["lesson"]["version"] == 1


async def test_update_lesson_substantive_cascades_quiz_item_retirement(
    client, db_session
):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson = await _create_lesson(client, token, deck_id)
    qi_resps = []
    for _ in range(3):
        r = await client.post(
            f"/api/v1/admin/lessons/{lesson['id']}/quiz-items",
            json={"question": "Q?", "answer": "A.", "question_type": "free_text"},
            headers=_auth(token),
        )
        assert r.status_code == 201
        qi_resps.append(r.json()["id"])

    # Replace concept_md with completely different content (substantive).
    new_concept = (
        "## Concept (rewritten)\n\n"
        "Entirely new content — bears almost no resemblance to the seed body. "
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris."
    )
    resp = await client.patch(
        f"/api/v1/admin/lessons/{lesson['id']}",
        json={
            "edit_classification": "substantive",
            "concept_md": new_concept,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version_type_applied"] == "substantive"
    assert body["quiz_items_retired_count"] == 3
    assert set(body["quiz_items_retired_ids"]) == set(qi_resps)
    assert body["lesson"]["version"] == 2
    assert body["lesson"]["version_type"] == "substantive_edit"

    # Verify DB rows reflect retirement.
    result = await db_session.execute(
        select(QuizItem).where(QuizItem.lesson_id == lesson["id"])
    )
    rows = result.scalars().all()
    assert len(rows) == 3
    assert all(r.retired_at is not None for r in rows)


async def test_update_lesson_409_classification_disagreement(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson = await _create_lesson(client, token, deck_id)
    new_concept = (
        "Entirely different content — admin claims minor but BE says substantive. "
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
    )
    resp = await client.patch(
        f"/api/v1/admin/lessons/{lesson['id']}",
        json={"edit_classification": "minor", "concept_md": new_concept},
        headers=_auth(token),
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["error"] == "edit_classification_mismatch"
    assert detail["expected"] == "substantive"
    assert detail["claimed"] == "minor"
    assert "concept_md" in detail["fields"]


async def test_publish_lesson_idempotent(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson = await _create_lesson(client, token, deck_id)
    first = await client.post(
        f"/api/v1/admin/lessons/{lesson['id']}/publish", headers=_auth(token)
    )
    assert first.status_code == 200
    assert first.json()["published_at"] is not None
    pub_at = first.json()["published_at"]
    second = await client.post(
        f"/api/v1/admin/lessons/{lesson['id']}/publish", headers=_auth(token)
    )
    assert second.status_code == 200
    assert second.json()["published_at"] == pub_at


async def test_publish_lesson_409_archived(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson = await _create_lesson(client, token, deck_id)
    archive = await client.post(
        f"/api/v1/admin/lessons/{lesson['id']}/archive", headers=_auth(token)
    )
    assert archive.status_code == 200
    publish = await client.post(
        f"/api/v1/admin/lessons/{lesson['id']}/publish", headers=_auth(token)
    )
    assert publish.status_code == 409


async def test_archive_lesson_does_not_cascade_retire(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    lesson = await _create_lesson(client, token, deck_id)
    qi_resp = await client.post(
        f"/api/v1/admin/lessons/{lesson['id']}/quiz-items",
        json={"question": "Q?", "answer": "A.", "question_type": "free_text"},
        headers=_auth(token),
    )
    assert qi_resp.status_code == 201
    qi_id = qi_resp.json()["id"]

    arch = await client.post(
        f"/api/v1/admin/lessons/{lesson['id']}/archive", headers=_auth(token)
    )
    assert arch.status_code == 200
    assert arch.json()["archived_at"] is not None

    # quiz_item must still be active.
    result = await db_session.execute(select(QuizItem).where(QuizItem.id == qi_id))
    qi = result.scalar_one()
    assert qi.retired_at is None


async def test_list_admin_lessons_status_filter_subset(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    draft = await _create_lesson(client, token, deck_id)
    pub = await _create_lesson(client, token, deck_id)
    archived = await _create_lesson(client, token, deck_id)
    await client.post(
        f"/api/v1/admin/lessons/{pub['id']}/publish", headers=_auth(token)
    )
    await client.post(
        f"/api/v1/admin/lessons/{archived['id']}/archive", headers=_auth(token)
    )

    drafts = await client.get(
        f"/api/v1/admin/decks/{deck_id}/lessons?status=drafts", headers=_auth(token)
    )
    draft_ids = {l["id"] for l in drafts.json()}
    assert draft["id"] in draft_ids
    assert pub["id"] not in draft_ids
    assert archived["id"] not in draft_ids

    published = await client.get(
        f"/api/v1/admin/decks/{deck_id}/lessons?status=published",
        headers=_auth(token),
    )
    pub_ids = {l["id"] for l in published.json()}
    assert pub["id"] in pub_ids
    assert draft["id"] not in pub_ids

    archived_list = await client.get(
        f"/api/v1/admin/decks/{deck_id}/lessons?status=archived",
        headers=_auth(token),
    )
    arch_ids = {l["id"] for l in archived_list.json()}
    assert archived["id"] in arch_ids


async def test_list_admin_lessons_rejects_invalid_status(client, db_session):
    token = await _sign_in_admin(client, db_session)
    deck_id = await _create_deck(client, token)
    resp = await client.get(
        f"/api/v1/admin/decks/{deck_id}/lessons?status=retired", headers=_auth(token)
    )
    assert resp.status_code == 422
