"""Integration tests for `GET /api/v1/learn/ranked-decks`.

Spec: docs/specs/phase-6/07-deck-lesson-ranker.md §10.2 + AC-3 + AC-7
+ §12 D-9 / D-10.

Mirrors the test_lesson_view_route.py ASGI client + auth-via-google-mock
pattern.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.deck import Deck
from app.models.subscription import Subscription
from app.models.tracker import TrackerApplicationModel
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


async def _sign_in(client, *, persona: str = "interview_prepper") -> tuple[str, str]:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@ranker-route-test.com",
        "name": "Ranker Route Tester",
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


async def _set_persona(db_session, user_id: str, persona: str) -> None:
    user = (await db_session.get(User, user_id))
    user.persona = persona
    await db_session.flush()


async def _set_plan(db_session, user_id: str, plan: str) -> None:
    """Mutate the auto-created Subscription from the auth flow.

    The Google sign-in handler creates a `free`/`active` Subscription
    on user upsert; tests that want a different plan flip the existing
    row instead of inserting a second one.
    """
    from sqlalchemy import select as _select

    existing = (
        await db_session.execute(
            _select(Subscription).where(Subscription.user_id == user_id)
        )
    ).scalar_one_or_none()
    if existing is None:
        db_session.add(
            Subscription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                plan=plan,
                status="active",
            )
        )
    else:
        existing.plan = plan
        existing.status = "active"
    await db_session.flush()


async def _seed_deck(
    db_session,
    *,
    slug: str | None = None,
    title: str = "RR Deck",
    persona_visibility: str = "both",
    tier: str = "foundation",
    display_order: int = 0,
) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=slug or f"deck-{uuid.uuid4().hex[:6]}",
        title=title,
        description="route-test deck",
        display_order=display_order,
        persona_visibility=persona_visibility,
        tier=tier,
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_scan(
    db_session,
    *,
    user_id: str,
    skill_gaps: list[dict],
) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company="Acme",
        role="Engineer",
        date_applied="2026-04-28",
        ats_score=70,
        status="Applied",
        scan_id=str(uuid.uuid4()),
        analysis_payload={"skill_gaps": skill_gaps},
    )
    db_session.add(row)
    await db_session.flush()
    return row


# ── Auth gate ─────────────────────────────────────────────────────────────────


async def test_get_ranked_decks_unauthed_returns_401(client, db_session):
    resp = await client.get("/api/v1/learn/ranked-decks")
    assert resp.status_code == 401


# ── Happy path (AC-3) ────────────────────────────────────────────────────────


async def test_get_ranked_decks_authed_returns_200(client, db_session):
    token, user_id = await _sign_in(client)
    await _set_persona(db_session, user_id, "interview_prepper")
    await _seed_deck(db_session, slug="rr-deck")

    resp = await client.get(
        "/api/v1/learn/ranked-decks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text


# ── Cold-start branch (AC-7) ─────────────────────────────────────────────────


async def test_get_ranked_decks_cold_start_response_well_formed(client, db_session):
    token, user_id = await _sign_in(client)
    await _set_persona(db_session, user_id, "interview_prepper")
    await _seed_deck(db_session, slug="cs-alpha", display_order=1)
    await _seed_deck(db_session, slug="cs-beta", display_order=2)

    resp = await client.get(
        "/api/v1/learn/ranked-decks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["cold_start"] is True
    assert data["recent_gap_count"] == 0
    assert data["lookback_days"] == 30
    assert data["lessons"] is None
    slugs = [d["deck"]["slug"] for d in data["decks"]]
    assert slugs[0] == "cs-alpha"  # display_order ASC.


# ── Query-param honours (D-14) ───────────────────────────────────────────────


async def test_get_ranked_decks_lookback_days_query_param_honored(client, db_session):
    token, user_id = await _sign_in(client)
    await _set_persona(db_session, user_id, "interview_prepper")
    await _seed_deck(db_session, slug="qp-alpha")

    # Seed an old scan that is excluded by lookback_days=7 but present
    # under the default 30-day window.
    row = await _seed_scan(
        db_session,
        user_id=user_id,
        skill_gaps=[
            {"skill": "Old", "category": "Tool", "importance": "critical"},
        ],
    )
    row.created_at = datetime.now() - timedelta(days=14)
    await db_session.flush()

    narrow = await client.get(
        "/api/v1/learn/ranked-decks?lookback_days=7",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert narrow.status_code == 200
    assert narrow.json()["recent_gap_count"] == 0
    assert narrow.json()["cold_start"] is True

    wide = await client.get(
        "/api/v1/learn/ranked-decks?lookback_days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wide.status_code == 200
    assert wide.json()["recent_gap_count"] == 1
    assert wide.json()["cold_start"] is False


async def test_get_ranked_decks_invalid_lookback_returns_400(client, db_session):
    token, _ = await _sign_in(client)
    resp = await client.get(
        "/api/v1/learn/ranked-decks?lookback_days=-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    # FastAPI/Pydantic Query validation surfaces as 422 by default —
    # bracket the assertion.
    assert resp.status_code in (400, 422)


# ── Schema regression (AC-2 / AC-3) ──────────────────────────────────────────


async def test_get_ranked_decks_response_matches_pydantic_schema(client, db_session):
    token, user_id = await _sign_in(client)
    await _set_persona(db_session, user_id, "interview_prepper")
    await _seed_deck(db_session, slug="schema-alpha")

    resp = await client.get(
        "/api/v1/learn/ranked-decks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "user_id",
        "persona",
        "cold_start",
        "lookback_days",
        "recent_gap_count",
        "ranked_at",
        "decks",
        "lessons",
    ):
        assert key in data
    if data["decks"]:
        deck_entry = data["decks"][0]
        for key in ("deck", "score", "rank", "matched_gaps", "score_breakdown"):
            assert key in deck_entry
        for key in (
            "gap_match",
            "fsrs_due",
            "avg_quality",
            "display_order_rank",
        ):
            assert key in deck_entry["score_breakdown"]


# ── AC-5: tier filtering doesn't leak premium decks to free users ────────────


async def test_get_ranked_decks_skips_premium_for_free_user(client, db_session):
    token, user_id = await _sign_in(client)
    await _set_persona(db_session, user_id, "interview_prepper")
    await _set_plan(db_session, user_id, "free")
    await _seed_deck(db_session, slug="free-foundation", tier="foundation")
    await _seed_deck(db_session, slug="leak-premium", tier="premium")

    resp = await client.get(
        "/api/v1/learn/ranked-decks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    slugs = {d["deck"]["slug"] for d in resp.json()["decks"]}
    assert "leak-premium" not in slugs
    assert "free-foundation" in slugs
