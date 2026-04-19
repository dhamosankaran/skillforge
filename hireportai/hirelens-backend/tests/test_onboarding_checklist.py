"""Onboarding checklist tests (Spec #41).

The checklist is a pure function of telemetry rows — no mocks needed
beyond the shared DB fixture. Every test seeds the minimum rows that
represent a completed step and asserts the derivation returns the
expected ``complete`` flag.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.mission import Mission
from app.models.tracker import TrackerApplicationModel
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    """HTTP client with the test DB session injected into FastAPI."""
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(loop_scope="session")
async def prepper_user(db_session) -> User:
    """Insert an Interview-Prepper user with a fresh id."""
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Prepper User",
        persona="interview_prepper",
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(loop_scope="session")
async def climber_user(db_session) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Climber User",
        persona="career_climber",
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(loop_scope="session")
async def team_lead_user(db_session) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Lead User",
        persona="team_lead",
        onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(loop_scope="session")
async def seeded_card(db_session) -> Card:
    """A single card + category so CardProgress rows can reference them."""
    category = Category(
        name=f"cat-{uuid.uuid4()}",
        icon="Star",
        color="#000",
        display_order=1,
        source="seeded",
    )
    db_session.add(category)
    await db_session.flush()

    card = Card(
        category_id=category.id,
        question="Q",
        answer="A",
        difficulty="medium",
        tags=[],
    )
    db_session.add(card)
    await db_session.flush()
    return card


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


# ── Step-level signals ──────────────────────────────────────────────────────


async def test_step_scan_resume_complete_when_tracker_row_exists(
    client, prepper_user, db_session
):
    db_session.add(
        TrackerApplicationModel(
            user_id=prepper_user.id,
            company="Acme",
            role="SWE",
            date_applied="2026-04-19",
            ats_score=70,
            scan_id=str(uuid.uuid4()),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    assert resp.status_code == 200, resp.text
    steps = {s["id"]: s for s in resp.json()["steps"]}
    assert steps["scan_resume"]["complete"] is True
    assert steps["pick_category"]["complete"] is False
    assert steps["review_gaps"]["complete"] is False
    assert steps["set_mission"]["complete"] is False
    assert steps["first_review"]["complete"] is False
    assert resp.json()["all_complete"] is False
    assert resp.json()["completed_at"] is None


async def test_step_pick_category_complete_when_card_progress_exists(
    client, prepper_user, seeded_card, db_session
):
    db_session.add(
        CardProgress(
            user_id=prepper_user.id,
            card_id=seeded_card.id,
            state="new",
            reps=0,
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    assert resp.status_code == 200, resp.text
    steps = {s["id"]: s for s in resp.json()["steps"]}
    assert steps["pick_category"]["complete"] is True


async def test_step_review_gaps_transitively_tracks_pick_category(
    client, prepper_user, seeded_card, db_session
):
    """Step 2 is transitive — it completes iff step 3 completes (spec §3.1)."""
    # No card_progress yet → both must be incomplete.
    resp_before = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    assert resp_before.status_code == 200
    steps_before = {s["id"]: s for s in resp_before.json()["steps"]}
    assert steps_before["review_gaps"]["complete"] is False
    assert steps_before["pick_category"]["complete"] is False

    # After a card_progress insert, both step 2 and step 3 flip to true.
    db_session.add(
        CardProgress(
            user_id=prepper_user.id,
            card_id=seeded_card.id,
            state="new",
            reps=0,
        )
    )
    await db_session.flush()

    resp_after = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    steps_after = {s["id"]: s for s in resp_after.json()["steps"]}
    assert steps_after["review_gaps"]["complete"] is True
    assert steps_after["pick_category"]["complete"] is True


async def test_step_set_mission_complete_when_mission_exists(
    client, prepper_user, db_session
):
    db_session.add(
        Mission(
            user_id=prepper_user.id,
            title="Interview at Acme",
            target_date=datetime.utcnow().date() + timedelta(days=30),
            daily_target=10,
            status="active",
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    steps = {s["id"]: s for s in resp.json()["steps"]}
    assert steps["set_mission"]["complete"] is True


async def test_step_first_review_complete_when_reps_gte_one(
    client, prepper_user, seeded_card, db_session
):
    db_session.add(
        CardProgress(
            user_id=prepper_user.id,
            card_id=seeded_card.id,
            state="review",
            reps=2,
            last_reviewed=datetime.now(tz=timezone.utc),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    steps = {s["id"]: s for s in resp.json()["steps"]}
    assert steps["first_review"]["complete"] is True
    # Picking a category is also implied (CardProgress row exists).
    assert steps["pick_category"]["complete"] is True


async def test_checklist_all_complete_with_completed_at_set(
    client, prepper_user, seeded_card, db_session
):
    """Seeds every signal; expects all_complete=true and completed_at set."""
    db_session.add(
        TrackerApplicationModel(
            user_id=prepper_user.id,
            company="Acme",
            role="SWE",
            date_applied="2026-04-19",
            ats_score=70,
            scan_id=str(uuid.uuid4()),
        )
    )
    db_session.add(
        Mission(
            user_id=prepper_user.id,
            title="Interview at Acme",
            target_date=datetime.utcnow().date() + timedelta(days=30),
            daily_target=10,
            status="active",
        )
    )
    db_session.add(
        CardProgress(
            user_id=prepper_user.id,
            card_id=seeded_card.id,
            state="review",
            reps=3,
            last_reviewed=datetime.now(tz=timezone.utc),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["all_complete"] is True
    assert body["completed_at"] is not None
    assert all(step["complete"] for step in body["steps"])


async def test_checklist_incomplete_returns_completed_at_null(
    client, prepper_user
):
    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["all_complete"] is False
    assert body["completed_at"] is None
    assert len(body["steps"]) == 5


async def test_checklist_response_preserves_fixed_step_order(
    client, prepper_user
):
    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(prepper_user)
    )
    body = resp.json()
    assert [s["id"] for s in body["steps"]] == [
        "scan_resume",
        "review_gaps",
        "pick_category",
        "set_mission",
        "first_review",
    ]


# ── Authorization ───────────────────────────────────────────────────────────


async def test_checklist_403_for_career_climber(client, climber_user):
    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(climber_user)
    )
    assert resp.status_code == 403


async def test_checklist_403_for_team_lead(client, team_lead_user):
    resp = await client.get(
        "/api/v1/onboarding/checklist", headers=_auth_header(team_lead_user)
    )
    assert resp.status_code == 403


async def test_checklist_401_for_unauth(client):
    resp = await client.get("/api/v1/onboarding/checklist")
    assert resp.status_code == 401
