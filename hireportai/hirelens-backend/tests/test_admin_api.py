"""Admin Card CRUD API tests.

Covers: create, update, soft-delete, hard-delete, 403 for non-admin,
bulk CSV import (all-or-nothing and partial mode), AI card generation.
"""
import io
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.db.session import get_db
from app.main import app
from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _sign_in(client, role: str = "user") -> tuple[str, str]:
    """Create a user via the auth endpoint; return (access_token, user_id)."""
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@admin-test.com",
        "name": "Admin Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    token = data["access_token"]
    user_id = data["user"]["id"]

    if role == "admin":
        # Promote to admin directly in the test DB
        from sqlalchemy import update as sql_update
        from app.models.user import User
        # We need the db_session — get it from the override
        db_gen = app.dependency_overrides[get_db]()
        db = await db_gen.__anext__()
        await db.execute(
            sql_update(User).where(User.id == user_id).values(role="admin")
        )
        await db.flush()

    return token, user_id


async def _seed_category(db_session) -> Category:
    suffix = uuid.uuid4().hex[:6]
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"TestCat-{suffix}",
        icon="T",
        color="from-gray-500 to-gray-600",
        display_order=99,
        source="foundation",
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ────────────────────────────────────────────────────────────────────

class TestAdminCreateCard:
    async def test_admin_can_create_card(self, client, db_session):
        token, _ = await _sign_in(client, role="admin")
        cat = await _seed_category(db_session)

        resp = await client.post("/api/v1/admin/cards", json={
            "category_id": cat.id,
            "question": "What is a hash table?",
            "answer": "A data structure that maps keys to values.",
            "difficulty": "easy",
            "tags": ["data-structures"],
        }, headers=_auth(token))

        assert resp.status_code == 201
        data = resp.json()
        assert data["question"] == "What is a hash table?"
        assert data["category_name"] == cat.name
        assert data["embedding_status"] == "pending"
        assert data["difficulty"] == "easy"
        assert data["tags"] == ["data-structures"]


class TestAdminUpdateCard:
    async def test_admin_can_update_card(self, client, db_session):
        token, _ = await _sign_in(client, role="admin")
        cat = await _seed_category(db_session)

        # Create a card first
        create_resp = await client.post("/api/v1/admin/cards", json={
            "category_id": cat.id,
            "question": "Original question",
            "answer": "Original answer",
            "difficulty": "medium",
        }, headers=_auth(token))
        card_id = create_resp.json()["id"]

        # Update the question
        resp = await client.put(f"/api/v1/admin/cards/{card_id}", json={
            "question": "Updated question",
        }, headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["question"] == "Updated question"
        assert data["answer"] == "Original answer"
        assert data["embedding_status"] == "pending"


class TestAdminDeleteCard:
    async def test_admin_can_delete_card_hard(self, client, db_session):
        """Card with no review history is hard-deleted."""
        token, _ = await _sign_in(client, role="admin")
        cat = await _seed_category(db_session)

        create_resp = await client.post("/api/v1/admin/cards", json={
            "category_id": cat.id,
            "question": "To be hard-deleted",
            "answer": "Gone",
            "difficulty": "easy",
        }, headers=_auth(token))
        card_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/admin/cards/{card_id}", headers=_auth(token))
        assert resp.status_code == 204

        # Card should be gone from DB entirely
        result = await db_session.execute(select(Card).where(Card.id == card_id))
        assert result.scalar_one_or_none() is None

    async def test_admin_can_delete_card_soft(self, client, db_session):
        """Card with review history is soft-deleted (deleted_at set)."""
        token, user_id = await _sign_in(client, role="admin")
        cat = await _seed_category(db_session)

        create_resp = await client.post("/api/v1/admin/cards", json={
            "category_id": cat.id,
            "question": "To be soft-deleted",
            "answer": "Still in DB",
            "difficulty": "medium",
        }, headers=_auth(token))
        card_id = create_resp.json()["id"]

        # Create a review record so the card has history
        progress = CardProgress(
            user_id=user_id,
            card_id=card_id,
        )
        db_session.add(progress)
        await db_session.flush()

        resp = await client.delete(f"/api/v1/admin/cards/{card_id}", headers=_auth(token))
        assert resp.status_code == 204

        # Card is still in DB but deleted_at is set
        result = await db_session.execute(select(Card).where(Card.id == card_id))
        card = result.scalar_one()
        assert card.deleted_at is not None


class TestNonAdminGets403:
    async def test_non_admin_gets_403(self, client, db_session):
        token, _ = await _sign_in(client, role="user")

        endpoints = [
            ("GET", "/api/v1/admin/cards"),
            ("POST", "/api/v1/admin/cards"),
            ("PUT", f"/api/v1/admin/cards/{uuid.uuid4()}"),
            ("DELETE", f"/api/v1/admin/cards/{uuid.uuid4()}"),
            ("POST", "/api/v1/admin/cards/import"),
        ]

        for method, url in endpoints:
            if method == "GET":
                resp = await client.get(url, headers=_auth(token))
            elif method == "POST" and "import" in url:
                resp = await client.post(url, headers=_auth(token), files={
                    "file": ("test.csv", b"category_id,question,answer,difficulty\n", "text/csv"),
                })
            elif method == "POST":
                resp = await client.post(url, json={
                    "category_id": str(uuid.uuid4()),
                    "question": "q", "answer": "a", "difficulty": "easy",
                }, headers=_auth(token))
            elif method == "PUT":
                resp = await client.put(url, json={"question": "q"}, headers=_auth(token))
            else:
                resp = await client.delete(url, headers=_auth(token))

            assert resp.status_code == 403, f"{method} {url} returned {resp.status_code}"


class TestBulkImport:
    async def test_bulk_import(self, client, db_session):
        token, _ = await _sign_in(client, role="admin")
        cat = await _seed_category(db_session)

        csv_content = (
            f"category_id,question,answer,difficulty,tags\n"
            f"{cat.id},\"What is X?\",\"X is Y\",easy,tag1;tag2\n"
            f"{cat.id},\"What is Z?\",\"Z is W\",medium,tag3\n"
        )

        resp = await client.post(
            "/api/v1/admin/cards/import",
            headers=_auth(token),
            files={"file": ("cards.csv", csv_content.encode(), "text/csv")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["created_count"] == 2
        assert data["skipped_count"] == 0
        assert data["errors"] == []

    async def test_bulk_import_partial_mode(self, client, db_session):
        token, _ = await _sign_in(client, role="admin")
        cat = await _seed_category(db_session)

        csv_content = (
            f"category_id,question,answer,difficulty,tags\n"
            f"{cat.id},\"Good question\",\"Good answer\",easy,\n"
            f"bad-id,\"Bad question\",\"Bad answer\",extreme,\n"
        )

        # Without partial — should fail with 400
        resp_strict = await client.post(
            "/api/v1/admin/cards/import?partial=false",
            headers=_auth(token),
            files={"file": ("cards.csv", csv_content.encode(), "text/csv")},
        )
        assert resp_strict.status_code == 400

        # With partial — valid rows inserted, invalid skipped
        resp_partial = await client.post(
            "/api/v1/admin/cards/import?partial=true",
            headers=_auth(token),
            files={"file": ("cards.csv", csv_content.encode(), "text/csv")},
        )
        assert resp_partial.status_code == 200
        data = resp_partial.json()
        assert data["created_count"] == 1
        assert data["skipped_count"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["row"] == 3


class TestAICardGeneration:
    async def test_generates_valid_card_structure(self, client, db_session):
        """Mock LLM returns valid JSON; endpoint returns a well-structured draft."""
        token, _ = await _sign_in(client, role="admin")

        mock_llm_response = json.dumps({
            "question": "What is the time complexity of binary search?",
            "answer": "O(log n). Binary search halves the search space at each step.",
            "tags": ["algorithms", "binary-search", "time-complexity"],
        })

        with patch(
            "app.services.ai_card_service.generate_for_task",
            return_value=mock_llm_response,
        ):
            resp = await client.post("/api/v1/admin/cards/generate", json={
                "topic": "Binary search",
                "difficulty": "medium",
            }, headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["question"] == "What is the time complexity of binary search?"
        assert "O(log n)" in data["answer"]
        assert data["difficulty"] == "medium"
        assert isinstance(data["tags"], list)
        assert len(data["tags"]) == 3
        assert "algorithms" in data["tags"]

    async def test_generate_non_admin_403(self, client, db_session):
        """Non-admin user gets 403 on the generate endpoint."""
        token, _ = await _sign_in(client, role="user")

        resp = await client.post("/api/v1/admin/cards/generate", json={
            "topic": "Binary search",
            "difficulty": "easy",
        }, headers=_auth(token))

        assert resp.status_code == 403

    async def test_generate_llm_failure_503(self, client, db_session):
        """LLM failure returns 503."""
        token, _ = await _sign_in(client, role="admin")

        with patch(
            "app.services.ai_card_service.generate_for_task",
            side_effect=RuntimeError("LLM down"),
        ):
            resp = await client.post("/api/v1/admin/cards/generate", json={
                "topic": "Merge sort",
                "difficulty": "hard",
            }, headers=_auth(token))

        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()
