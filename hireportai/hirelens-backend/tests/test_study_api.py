"""Integration tests for the Study API routes.

Covers:
  GET  /api/v1/study/daily
  POST /api/v1/study/review
  GET  /api/v1/study/progress

Uses the same ASGI client + db_session override pattern as test_cards_api.py.
All database writes are flushed (not committed) and rolled back after the
session, so tests are fully isolated.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Client fixture ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    """ASGI client wired to the test db_session (same rollback-on-teardown session)."""

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── Seed helpers ──────────────────────────────────────────────────────────────


async def _sign_in(client, google_id: str | None = None) -> tuple[str, str]:
    """Create a user via the auth endpoint; return (access_token, user_id)."""
    info = {
        "google_id": google_id or f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@study-api-test.com",
        "name": "Study API Tester",
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


async def _seed_category(db_session, source: str = "foundation") -> Category:
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"Cat-{uuid.uuid4().hex[:6]}",
        icon="📚",
        color="from-blue-500 to-indigo-600",
        display_order=99,
        source=source,
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


async def _seed_card(db_session, category_id: str) -> Card:
    card = Card(
        id=str(uuid.uuid4()),
        category_id=category_id,
        question=f"Q-{uuid.uuid4().hex[:6]}?",
        answer="Test answer.",
        difficulty="medium",
        tags=[],
    )
    db_session.add(card)
    await db_session.flush()
    return card


async def _seed_progress(
    db_session,
    user_id: str,
    card_id: str,
    *,
    state: str = "review",
    due_delta_hours: float = -1.0,
) -> CardProgress:
    now = datetime.now(timezone.utc)
    cp = CardProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        card_id=card_id,
        state=state,
        stability=5.0,
        difficulty_fsrs=5.0,
        elapsed_days=0.0,
        scheduled_days=5.0,
        reps=2,
        lapses=0,
        due_date=now + timedelta(hours=due_delta_hours),
        last_reviewed=now - timedelta(days=5),
    )
    db_session.add(cp)
    await db_session.flush()
    return cp


# ── Auth guard tests ──────────────────────────────────────────────────────────


class TestRequiresAuth:
    async def test_daily_returns_401_without_token(self, client):
        """GET /study/daily must return 401 when no bearer token is provided."""
        resp = await client.get("/api/v1/study/daily")
        assert resp.status_code == 401

    async def test_review_returns_401_without_token(self, client):
        """POST /study/review must return 401 when no bearer token is provided."""
        resp = await client.post(
            "/api/v1/study/review",
            json={"card_id": str(uuid.uuid4()), "rating": 3, "session_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401

    async def test_progress_returns_401_without_token(self, client):
        """GET /study/progress must return 401 when no bearer token is provided."""
        resp = await client.get("/api/v1/study/progress")
        assert resp.status_code == 401


# ── Daily review tests ────────────────────────────────────────────────────────


class TestGetDailyReview:
    async def test_returns_overdue_card(self, client, db_session):
        """Overdue card_progress row appears in the daily queue."""
        token, user_id = await _sign_in(client)
        cat = await _seed_category(db_session, source="foundation")
        card = await _seed_card(db_session, cat.id)
        await _seed_progress(db_session, user_id, card.id, state="review", due_delta_hours=-24.0)

        resp = await client.get(
            "/api/v1/study/daily",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "cards" in data
        assert "session_id" in data
        card_ids = [c["card_id"] for c in data["cards"]]
        assert card.id in card_ids

    async def test_returns_new_card_for_fresh_user(self, client, db_session):
        """A user with no progress rows gets unreviewed cards in the queue."""
        token, _ = await _sign_in(client)
        cat = await _seed_category(db_session, source="foundation")
        card = await _seed_card(db_session, cat.id)

        resp = await client.get(
            "/api/v1/study/daily",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        card_ids = [c["card_id"] for c in data["cards"]]
        assert card.id in card_ids
        # The card should show up as "new" (never reviewed)
        matched = next(c for c in data["cards"] if c["card_id"] == card.id)
        assert matched["fsrs_state"] == "new"

    async def test_capped_at_five_cards(self, client, db_session):
        """Daily queue never returns more than 5 cards regardless of overdue count."""
        token, user_id = await _sign_in(client)
        cat = await _seed_category(db_session, source="foundation")
        for _ in range(8):
            card = await _seed_card(db_session, cat.id)
            await _seed_progress(
                db_session, user_id, card.id, state="review", due_delta_hours=-24.0
            )

        resp = await client.get(
            "/api/v1/study/daily",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert len(resp.json()["cards"]) <= 5

    async def test_free_user_does_not_see_premium_cards(self, client, db_session):
        """Free-plan users must not receive cards from non-foundation categories."""
        token, user_id = await _sign_in(client)
        premium_cat = await _seed_category(db_session, source="premium")
        premium_card = await _seed_card(db_session, premium_cat.id)
        await _seed_progress(
            db_session, user_id, premium_card.id, state="review", due_delta_hours=-24.0
        )

        resp = await client.get(
            "/api/v1/study/daily",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        card_ids = [c["card_id"] for c in resp.json()["cards"]]
        assert premium_card.id not in card_ids


# ── Review submission tests ───────────────────────────────────────────────────


class TestSubmitReview:
    async def test_review_card_returns_fsrs_state(self, client, db_session):
        """POST /study/review returns the updated FSRS scheduling state."""
        token, user_id = await _sign_in(client)
        cat = await _seed_category(db_session, source="foundation")
        card = await _seed_card(db_session, cat.id)
        await _seed_progress(db_session, user_id, card.id, state="review")

        resp = await client.post(
            "/api/v1/study/review",
            json={
                "card_id": card.id,
                "rating": 3,  # Good
                "session_id": str(uuid.uuid4()),
                "time_spent_ms": 3000,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["card_id"] == card.id
        assert data["fsrs_state"] in ("learning", "review", "relearning")
        assert "due_date" in data
        assert "stability" in data
        assert data["reps"] >= 1

    async def test_review_advances_schedule(self, client, db_session):
        """Good (3) rating on a Review card schedules next review ≥ 1 day out."""
        token, user_id = await _sign_in(client)
        cat = await _seed_category(db_session, source="foundation")
        card = await _seed_card(db_session, cat.id)
        await _seed_progress(db_session, user_id, card.id, state="review")

        resp = await client.post(
            "/api/v1/study/review",
            json={"card_id": card.id, "rating": 3, "session_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert resp.json()["scheduled_days"] >= 1.0

    async def test_review_nonexistent_card_returns_404(self, client, db_session):
        """POST /study/review with an unknown card_id must return 404."""
        token, _ = await _sign_in(client)

        resp = await client.post(
            "/api/v1/study/review",
            json={
                "card_id": str(uuid.uuid4()),  # bogus
                "rating": 3,
                "session_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 404

    async def test_review_invalid_rating_returns_422(self, client, db_session):
        """Rating outside [1, 4] is rejected by Pydantic validation (422)."""
        token, _ = await _sign_in(client)

        resp = await client.post(
            "/api/v1/study/review",
            json={"card_id": str(uuid.uuid4()), "rating": 5, "session_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 422

    async def test_free_user_review_premium_card_returns_403(self, client, db_session):
        """Free-plan user submitting a review for a premium card gets 403."""
        token, user_id = await _sign_in(client)
        premium_cat = await _seed_category(db_session, source="premium")
        premium_card = await _seed_card(db_session, premium_cat.id)

        resp = await client.post(
            "/api/v1/study/review",
            json={
                "card_id": premium_card.id,
                "rating": 3,
                "session_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403


# ── Progress tests ────────────────────────────────────────────────────────────


class TestGetProgress:
    async def test_returns_progress_structure(self, client, db_session):
        """GET /study/progress returns a correctly shaped response."""
        token, user_id = await _sign_in(client)
        cat = await _seed_category(db_session, source="foundation")
        card = await _seed_card(db_session, cat.id)
        await _seed_progress(db_session, user_id, card.id, state="review")

        resp = await client.get(
            "/api/v1/study/progress",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "total_reviewed" in data
        assert "by_state" in data
        assert "total_reps" in data
        assert "total_lapses" in data
        # by_state must cover all four FSRS states
        for key in ("new", "learning", "review", "relearning"):
            assert key in data["by_state"]

    async def test_review_card_appears_in_progress(self, client, db_session):
        """After submitting a review, the card is counted in progress stats."""
        token, user_id = await _sign_in(client)
        cat = await _seed_category(db_session, source="foundation")
        card = await _seed_card(db_session, cat.id)

        # No progress yet
        before = (
            await client.get(
                "/api/v1/study/progress",
                headers={"Authorization": f"Bearer {token}"},
            )
        ).json()
        assert before["total_reviewed"] == 0

        # Submit first review
        await client.post(
            "/api/v1/study/review",
            json={"card_id": card.id, "rating": 3, "session_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )

        after = (
            await client.get(
                "/api/v1/study/progress",
                headers={"Authorization": f"Bearer {token}"},
            )
        ).json()
        assert after["total_reviewed"] >= 1
        assert after["total_reps"] >= 1
