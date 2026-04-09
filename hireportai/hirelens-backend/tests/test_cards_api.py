"""Cards API integration tests.

Covers all four endpoints:
  GET /api/v1/cards
  GET /api/v1/cards/search
  GET /api/v1/cards/category/{id}
  GET /api/v1/cards/{id}

Data is created directly in the shared test session (same pattern as
test_user_roles.py) so no separate fixtures file is needed.  Every test
rolls back on teardown via the conftest ``db_session`` fixture.
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text, update

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.card import Card
from app.models.category import Category
from app.models.subscription import Subscription

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ── Embedding constants ───────────────────────────────────────────────────────

_DIMS = 1536
# Unit vector along the first axis — easy to replicate in mock
_UNIT_VEC: list[float] = [1.0] + [0.0] * (_DIMS - 1)
_UNIT_VEC_STR = f"[{','.join(str(v) for v in _UNIT_VEC)}]"


# ── Client fixture ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    """HTTP client wired to the test session (same rollback-on-teardown session)."""
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _sign_in(client, google_id: str | None = None) -> tuple[str, str]:
    """Create a user via the auth endpoint; return (access_token, user_id)."""
    info = {
        "google_id": google_id or f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@cards-test.com",
        "name": "Cards Tester",
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


async def _seed(db_session) -> tuple[Category, Category, Card, Card]:
    """Insert one foundation + one premium category, each with one card.

    Uses unique name suffixes so parallel test sessions never conflict.
    """
    suffix = uuid.uuid4().hex[:6]

    f_cat = Category(
        id=str(uuid.uuid4()),
        name=f"SystemDesign-{suffix}",
        icon="🏗️",
        color="from-purple-500 to-indigo-600",
        display_order=10,
        source="foundation",
    )
    p_cat = Category(
        id=str(uuid.uuid4()),
        name=f"AdvancedAI-{suffix}",
        icon="🤖",
        color="from-blue-500 to-cyan-600",
        display_order=11,
        source="premium",
    )
    db_session.add_all([f_cat, p_cat])
    await db_session.flush()

    f_card = Card(
        id=str(uuid.uuid4()),
        category_id=f_cat.id,
        question="What is CAP theorem?",
        answer="Consistency, Availability, Partition tolerance — pick two.",
        difficulty="medium",
        tags=["distributed-systems"],
    )
    p_card = Card(
        id=str(uuid.uuid4()),
        category_id=p_cat.id,
        question="Explain transformer self-attention.",
        answer="Self-attention weighs token relationships via Q, K, V matrices.",
        difficulty="hard",
        tags=["ai", "ml"],
    )
    db_session.add_all([f_card, p_card])
    await db_session.flush()

    return f_cat, p_cat, f_card, p_card


async def _upgrade_to_pro(db_session, user_id: str) -> None:
    await db_session.execute(
        update(Subscription).where(Subscription.user_id == user_id).values(plan="pro")
    )
    await db_session.flush()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRequiresAuth:
    async def test_all_four_endpoints_return_401_without_token(self, client):
        """Every cards endpoint rejects unauthenticated requests with 401."""
        r1 = await client.get("/api/v1/cards")
        r2 = await client.get(f"/api/v1/cards/{uuid.uuid4()}")
        r3 = await client.get(f"/api/v1/cards/category/{uuid.uuid4()}")
        r4 = await client.get("/api/v1/cards/search?q=test")

        assert r1.status_code == 401  # assertion 1
        assert r2.status_code == 401  # assertion 2
        assert r3.status_code == 401  # assertion 3
        assert r4.status_code == 401  # assertion 4


class TestListCategories:
    async def test_pro_user_sees_all_categories(self, client, db_session):
        """Pro-plan user receives both foundation and premium categories."""
        token, user_id = await _sign_in(client)
        await _upgrade_to_pro(db_session, user_id)
        f_cat, p_cat, _, _ = await _seed(db_session)

        resp = await client.get(
            "/api/v1/cards", headers={"Authorization": f"Bearer {token}"}
        )

        assert resp.status_code == 200                          # assertion 5
        data = resp.json()
        assert "categories" in data                            # assertion 6
        ids = [c["id"] for c in data["categories"]]
        assert f_cat.id in ids                                 # assertion 7
        assert p_cat.id in ids                                 # assertion 8
        for cat in data["categories"]:
            assert "card_count" in cat                         # assertion 9
            assert isinstance(cat["card_count"], int)

    async def test_free_user_sees_only_foundation(self, client, db_session):
        """Free-plan user only receives categories where source='foundation'."""
        token, _ = await _sign_in(client)
        f_cat, p_cat, _, _ = await _seed(db_session)

        resp = await client.get(
            "/api/v1/cards", headers={"Authorization": f"Bearer {token}"}
        )

        assert resp.status_code == 200                          # assertion 10
        cats = resp.json()["categories"]
        ids = [c["id"] for c in cats]
        assert f_cat.id in ids                                 # assertion 11
        assert p_cat.id not in ids                             # assertion 12
        non_foundation = [c for c in cats if c["source"] != "foundation"]
        assert non_foundation == []                            # assertion 13


class TestGetCardsByCategory:
    async def test_returns_cards_and_metadata(self, client, db_session):
        """Accessible category returns category metadata, card list, and total."""
        token, user_id = await _sign_in(client)
        await _upgrade_to_pro(db_session, user_id)
        f_cat, _, f_card, _ = await _seed(db_session)

        resp = await client.get(
            f"/api/v1/cards/category/{f_cat.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200                          # assertion 14
        data = resp.json()
        assert data["category"]["id"] == f_cat.id              # assertion 15
        assert data["total"] >= 1                              # assertion 16
        card_ids = [c["id"] for c in data["cards"]]
        assert f_card.id in card_ids                           # assertion 17
        for card in data["cards"]:
            assert "embedding" not in card                     # assertion 18

    async def test_free_user_blocked_from_premium_category(self, client, db_session):
        """Free user requesting a premium category gets 403."""
        token, _ = await _sign_in(client)
        _, p_cat, _, _ = await _seed(db_session)

        resp = await client.get(
            f"/api/v1/cards/category/{p_cat.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403                          # assertion 19

    async def test_nonexistent_category_returns_404(self, client):
        token, _ = await _sign_in(client)
        resp = await client.get(
            f"/api/v1/cards/category/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404                          # assertion 20


class TestGetCard:
    async def test_returns_card_with_category_name(self, client, db_session):
        """Single card response includes category_name; embedding is absent."""
        token, user_id = await _sign_in(client)
        await _upgrade_to_pro(db_session, user_id)
        f_cat, _, f_card, _ = await _seed(db_session)

        resp = await client.get(
            f"/api/v1/cards/{f_card.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200                          # assertion 21
        data = resp.json()
        assert data["id"] == f_card.id                         # assertion 22
        assert data["category_id"] == f_cat.id                # assertion 23
        assert data["category_name"] == f_cat.name            # assertion 24
        assert "embedding" not in data                         # assertion 25

    async def test_free_user_blocked_from_premium_card(self, client, db_session):
        """Free user requesting a card from a premium category gets 403."""
        token, _ = await _sign_in(client)
        _, _, _, p_card = await _seed(db_session)

        resp = await client.get(
            f"/api/v1/cards/{p_card.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403                          # assertion 26

    async def test_nonexistent_card_returns_404(self, client):
        token, _ = await _sign_in(client)
        resp = await client.get(
            f"/api/v1/cards/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404                          # assertion 27


class TestSearchCards:
    async def test_search_returns_ranked_results(self, client, db_session):
        """Search with a mocked embed returns scored results; no embedding in output."""
        token, _ = await _sign_in(client)
        f_cat, _, f_card, _ = await _seed(db_session)

        # Store a synthetic unit-vector embedding on the foundation card
        await db_session.execute(
            text("UPDATE cards SET embedding = CAST(:vec AS vector) WHERE id = :id"),
            {"vec": _UNIT_VEC_STR, "id": f_card.id},
        )
        await db_session.flush()

        # Mock Gemini to return the exact same vector (cosine sim = 1.0)
        with patch("app.services.card_service._embed_sync", return_value=_UNIT_VEC):
            resp = await client.get(
                "/api/v1/cards/search?q=CAP+theorem",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200                          # assertion 28
        data = resp.json()
        assert data["query"] == "CAP theorem"                  # assertion 29
        assert isinstance(data["results"], list)               # assertion 30
        assert data["total"] == len(data["results"])           # assertion 31
        assert len(data["results"]) >= 1                       # assertion 32
        top = data["results"][0]
        assert top["id"] == f_card.id                         # assertion 33
        assert 0.0 <= top["score"] <= 1.0                     # assertion 34
        assert "embedding" not in top                          # assertion 35

    async def test_search_missing_q_returns_400(self, client):
        """Omitting the required `q` param returns 422 (FastAPI validation)."""
        token, _ = await _sign_in(client)
        resp = await client.get(
            "/api/v1/cards/search",
            headers={"Authorization": f"Bearer {token}"},
        )
        # FastAPI returns 422 for missing required query params
        assert resp.status_code == 422                          # assertion 36

    async def test_search_limit_out_of_range_returns_422(self, client):
        """limit=0 and limit=51 are rejected by FastAPI query validation."""
        token, _ = await _sign_in(client)
        headers = {"Authorization": f"Bearer {token}"}
        r_low = await client.get("/api/v1/cards/search?q=test&limit=0", headers=headers)
        r_high = await client.get("/api/v1/cards/search?q=test&limit=51", headers=headers)
        assert r_low.status_code == 422                        # assertion 37
        assert r_high.status_code == 422                       # assertion 38
