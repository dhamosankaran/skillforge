"""GET /api/v1/tracker/{id}/scores route tests (E-043 / spec #63 §6.4).

Covers AC-10 from §11. AC-3 D-3 unpaginated full-history return is
verified implicitly by the empty/single/multi-row tests.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.subscription import Subscription
from app.models.tracker import TrackerApplicationModel
from app.models.tracker_application_score import TrackerApplicationScore
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
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


async def _seed_user(db_session) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="History Test",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Subscription(user_id=user.id, plan="free", status="active"))
    await db_session.flush()
    return user


async def _seed_tracker(db_session, *, user_id: str) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        user_id=user_id,
        company="Acme",
        role="Backend",
        date_applied="2026-04-30",
        ats_score=0,
        status="Applied",
    )
    db_session.add(row)
    await db_session.flush()
    return row


def _auth(user: User) -> dict[str, str]:
    tok = create_access_token({"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {tok}"}


async def test_history_unauthed_returns_401(client, db_session):
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_id=user.id)
    resp = await client.get(f"/api/v1/tracker/{tracker.id}/scores")
    assert resp.status_code == 401


async def test_history_cross_user_returns_404(client, db_session):
    owner = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_id=owner.id)
    intruder = await _seed_user(db_session)
    resp = await client.get(
        f"/api/v1/tracker/{tracker.id}/scores", headers=_auth(intruder)
    )
    assert resp.status_code == 404


async def test_history_empty_returns_empty_list_and_null_delta(
    client, db_session
):
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_id=user.id)

    resp = await client.get(
        f"/api/v1/tracker/{tracker.id}/scores", headers=_auth(user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tracker_application_id"] == tracker.id
    assert body["history"] == []
    assert body["delta"] is None


async def test_history_returns_chronological_oldest_first_with_delta(
    client, db_session
):
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_id=user.id)

    base = datetime.now(timezone.utc) - timedelta(days=4)
    for i, score in enumerate([60, 75, 88]):
        db_session.add(
            TrackerApplicationScore(
                tracker_application_id=tracker.id,
                user_id=user.id,
                scan_id=f"s-{i}",
                overall_score=score,
                keyword_match_score=0.5 + i * 0.1,
                skills_coverage_score=0.6,
                formatting_compliance_score=0.9,
                bullet_strength_score=0.4,
                jd_hash="jh",
                resume_hash=f"rh-{i}",
                scanned_at=base + timedelta(days=i * 2),
            )
        )
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/tracker/{tracker.id}/scores", headers=_auth(user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [r["overall_score"] for r in body["history"]] == [60, 75, 88]
    assert body["delta"] is not None
    assert body["delta"]["overall_delta"] == 13  # latest two: 88 - 75
    assert body["delta"]["days_between"] == 2
