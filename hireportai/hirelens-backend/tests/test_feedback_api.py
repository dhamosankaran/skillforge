"""Per-card feedback API tests.

Covers: submit feedback, admin list, admin summary, non-admin 403.
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.card import Card
from app.models.card_feedback import CardFeedback
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
        "email": f"{uuid.uuid4()}@feedback-test.com",
        "name": "Feedback Tester",
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
        from sqlalchemy import update as sql_update
        from app.models.user import User

        db_gen = app.dependency_overrides[get_db]()
        db = await db_gen.__anext__()
        await db.execute(
            sql_update(User).where(User.id == user_id).values(role="admin")
        )
        await db.flush()

    return token, user_id


async def _seed_card(db_session) -> Card:
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"FBCat-{uuid.uuid4().hex[:6]}",
        icon="T",
        color="from-gray-500 to-gray-600",
        display_order=99,
        source="foundation",
    )
    db_session.add(cat)
    await db_session.flush()

    card = Card(
        id=str(uuid.uuid4()),
        category_id=cat.id,
        question="What is feedback?",
        answer="User input on card quality.",
        difficulty="easy",
        tags=[],
    )
    db_session.add(card)
    await db_session.flush()
    return card


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ────────────────────────────────────────────────────────────────────

class TestSubmitFeedback:
    async def test_submit_feedback(self, client, db_session):
        token, user_id = await _sign_in(client)
        card = await _seed_card(db_session)

        resp = await client.post(
            f"/api/v1/cards/{card.id}/feedback",
            json={"vote": "up", "comment": "Great card!"},
            headers=_auth(token),
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["vote"] == "up"
        assert data["comment"] == "Great card!"
        assert data["card_id"] == card.id
        assert data["user_id"] == user_id

    async def test_submit_downvote_without_comment(self, client, db_session):
        token, _ = await _sign_in(client)
        card = await _seed_card(db_session)

        resp = await client.post(
            f"/api/v1/cards/{card.id}/feedback",
            json={"vote": "down"},
            headers=_auth(token),
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["vote"] == "down"
        assert data["comment"] is None

    async def test_submit_feedback_invalid_vote(self, client, db_session):
        token, _ = await _sign_in(client)
        card = await _seed_card(db_session)

        resp = await client.post(
            f"/api/v1/cards/{card.id}/feedback",
            json={"vote": "maybe"},
            headers=_auth(token),
        )

        assert resp.status_code == 422

    async def test_submit_feedback_card_not_found(self, client, db_session):
        token, _ = await _sign_in(client)

        resp = await client.post(
            f"/api/v1/cards/{uuid.uuid4()}/feedback",
            json={"vote": "up"},
            headers=_auth(token),
        )

        assert resp.status_code == 404

    async def test_submit_feedback_requires_auth(self, client, db_session):
        card = await _seed_card(db_session)

        resp = await client.post(
            f"/api/v1/cards/{card.id}/feedback",
            json={"vote": "up"},
        )

        assert resp.status_code == 401


class TestAdminFeedbackList:
    async def test_admin_can_view_feedback(self, client, db_session):
        # Submit some feedback as a normal user
        user_token, _ = await _sign_in(client, role="user")
        card = await _seed_card(db_session)

        await client.post(
            f"/api/v1/cards/{card.id}/feedback",
            json={"vote": "down", "comment": "Confusing question"},
            headers=_auth(user_token),
        )

        # Now check as admin
        admin_token, _ = await _sign_in(client, role="admin")

        resp = await client.get(
            "/api/v1/admin/feedback",
            headers=_auth(admin_token),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["feedback"]) >= 1

    async def test_admin_can_filter_by_vote(self, client, db_session):
        admin_token, _ = await _sign_in(client, role="admin")

        resp = await client.get(
            "/api/v1/admin/feedback?vote=down",
            headers=_auth(admin_token),
        )

        assert resp.status_code == 200
        data = resp.json()
        for f in data["feedback"]:
            assert f["vote"] == "down"

    async def test_non_admin_cannot_view_feedback(self, client, db_session):
        token, _ = await _sign_in(client, role="user")

        resp = await client.get(
            "/api/v1/admin/feedback",
            headers=_auth(token),
        )

        assert resp.status_code == 403


class TestFeedbackSummary:
    async def test_feedback_summary_returns_worst_cards(self, client, db_session):
        user_token, user_id = await _sign_in(client, role="user")
        card = await _seed_card(db_session)

        # Submit multiple downvotes on the same card
        for _ in range(3):
            fb = CardFeedback(
                user_id=user_id,
                card_id=card.id,
                vote="down",
                comment="Bad card",
            )
            db_session.add(fb)
        await db_session.flush()

        admin_token, _ = await _sign_in(client, role="admin")

        resp = await client.get(
            "/api/v1/admin/feedback/summary",
            headers=_auth(admin_token),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["total_up"], int)
        assert isinstance(data["total_down"], int)
        assert data["total_down"] >= 3
        assert isinstance(data["worst_cards"], list)
        # Our card should appear in worst_cards
        worst_ids = [wc["card_id"] for wc in data["worst_cards"]]
        assert card.id in worst_ids
        # Check the structure
        for wc in data["worst_cards"]:
            assert "card_id" in wc
            assert "question" in wc
            assert "down_count" in wc
            assert wc["down_count"] >= 1

    async def test_non_admin_cannot_view_summary(self, client, db_session):
        token, _ = await _sign_in(client, role="user")

        resp = await client.get(
            "/api/v1/admin/feedback/summary",
            headers=_auth(token),
        )

        assert resp.status_code == 403
