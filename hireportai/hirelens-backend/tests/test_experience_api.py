"""AI experience generator API tests."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

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

async def _sign_in(client) -> tuple[str, str]:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@exp-test.com",
        "name": "Experience Tester",
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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _seed_study_history(db_session, user_id: str) -> int:
    """Create a category, cards, and card_progress rows to simulate study."""
    cat = Category(
        id=str(uuid.uuid4()),
        name="System Design",
        icon="S",
        color="from-blue-500 to-blue-600",
        display_order=1,
        source="foundation",
    )
    db_session.add(cat)
    await db_session.flush()

    cards_studied = 0
    for i in range(5):
        card = Card(
            id=str(uuid.uuid4()),
            category_id=cat.id,
            question=f"SD question {i}",
            answer=f"SD answer {i}",
            difficulty="medium",
            tags=["system-design"],
        )
        db_session.add(card)
        await db_session.flush()

        progress = CardProgress(
            id=str(uuid.uuid4()),
            user_id=user_id,
            card_id=card.id,
            state="review",
            stability=5.0,
            difficulty_fsrs=5.0,
            elapsed_days=1.0,
            scheduled_days=3.0,
            reps=3,
            lapses=0,
        )
        db_session.add(progress)
        cards_studied += 1

    await db_session.flush()
    return cards_studied


# ── Tests ────────────────────────────────────────────────────────────────────

class TestGenerateExperience:
    async def test_generates_experience_from_study_history(self, client, db_session):
        token, user_id = await _sign_in(client)
        await _seed_study_history(db_session, user_id)

        mock_llm_response = json.dumps({
            "experience_text": "Demonstrated strong proficiency in system design through completion of 5 expert-curated assessments with 100% accuracy, covering distributed systems architecture and scalability patterns.",
            "summary": "Strong in system design fundamentals.",
        })

        with patch(
            "app.services.experience_service.generate_for_task",
            return_value=mock_llm_response,
        ) as mock_generate:
            resp = await client.post(
                "/api/v1/study/experience",
                json={"topic": "system design"},
                headers=_auth(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "system design" in data["experience_text"].lower()
        assert data["summary"] != ""
        assert data["cards_studied"] == 5

        # Verify the LLM was called with a prompt containing the study stats
        call_args = mock_generate.call_args
        # generate_for_task is called positionally via asyncio.to_thread
        prompt = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("prompt", "")
        assert "System Design" in prompt
        assert "5" in prompt  # cards_studied count

    async def test_experience_requires_auth(self, client, db_session):
        resp = await client.post(
            "/api/v1/study/experience",
            json={"topic": "algorithms"},
        )
        assert resp.status_code == 401

    async def test_experience_with_no_study_history(self, client, db_session):
        token, _ = await _sign_in(client)

        resp = await client.post(
            "/api/v1/study/experience",
            json={},
            headers=_auth(token),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["cards_studied"] == 0
        assert "Start studying" in data["experience_text"]

    async def test_experience_llm_failure_returns_503(self, client, db_session):
        token, user_id = await _sign_in(client)
        await _seed_study_history(db_session, user_id)

        with patch(
            "app.services.experience_service.generate_for_task",
            side_effect=RuntimeError("LLM down"),
        ):
            resp = await client.post(
                "/api/v1/study/experience",
                json={"topic": "algorithms"},
                headers=_auth(token),
            )

        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()
