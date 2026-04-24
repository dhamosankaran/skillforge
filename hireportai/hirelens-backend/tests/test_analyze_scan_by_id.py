"""Spec #59 AC-2 / AC-4 / AC-5 — integration tests for GET /analyze/{scan_id}.

Covers the four response branches:
- 401 anonymous
- 404 unknown scan_id
- 404 cross-user (LD-4 — don't leak existence with 403)
- 410 legacy (analysis_payload IS NULL, pre-spec-59 row)
- 200 owner + payload populated → full AnalysisResponse round-trip

Mount-parity: the handler is registered on the legacy router and
re-exported by the v1 shim. Tests hit `/api/v1/analyze/{scan_id}` — the
canonical path per spec §7 — so accidental future changes to the v1
surface are caught.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate
from app.services.tracker_service_v2 import create_application

pytestmark = pytest.mark.asyncio(loop_scope="session")


_SAMPLE_PAYLOAD = {
    "scan_id": "placeholder-overridden-per-test",
    "ats_score": 81,
    "grade": "A",
    "score_breakdown": {
        "keyword_match": 80.0,
        "skills_coverage": 85.0,
        "formatting_compliance": 90.0,
        "bullet_strength": 70.0,
    },
    "matched_keywords": ["python", "fastapi", "postgres"],
    "missing_keywords": ["kubernetes"],
    "skill_gaps": [
        {"skill": "Kubernetes", "category": "Technical", "importance": "critical"}
    ],
    "bullet_analysis": [],
    "formatting_issues": [],
    "job_fit_explanation": "Strong alignment on backend stack.",
    "top_strengths": ["python", "fastapi"],
    "top_gaps": ["kubernetes"],
    "keyword_chart_data": [],
    "skills_overlap_data": [],
    "resume_text": "Sample resume.",
}


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


async def _seed_user(db_session, *, plan: str = "free") -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Scan GET Test",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Subscription(user_id=user.id, plan=plan, status="active"))
    await db_session.flush()
    await db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    tok = create_access_token({"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {tok}"}


async def _seed_scan(
    db_session, user: User, *, with_payload: bool = True
) -> str:
    scan_id = str(uuid.uuid4())
    payload = {**_SAMPLE_PAYLOAD, "scan_id": scan_id} if with_payload else None
    await create_application(
        TrackerApplicationCreate(
            company="AcmeCo",
            role="SWE",
            date_applied="2026-04-24",
            ats_score=81,
            status="Applied",
            scan_id=scan_id,
        ),
        db_session,
        user_id=user.id,
        analysis_payload=payload,
    )
    return scan_id


async def test_anonymous_call_returns_401(client):
    """Auth precedes ownership check — no scan_id leakage either way."""
    r = await client.get(f"/api/v1/analyze/{uuid.uuid4()}")
    assert r.status_code == 401


async def test_unknown_scan_id_returns_404(client, db_session):
    user = await _seed_user(db_session)
    r = await client.get(f"/api/v1/analyze/{uuid.uuid4()}", headers=_auth(user))
    assert r.status_code == 404
    body = r.json()
    assert body["detail"]["error"] == "scan_not_found"


async def test_cross_user_scan_returns_404_not_403(client, db_session):
    """LD-4 — ownership mismatch must return 404, never 403, to prevent
    existence-leakage via status-code differential."""
    owner = await _seed_user(db_session)
    stranger = await _seed_user(db_session)
    scan_id = await _seed_scan(db_session, owner)

    r = await client.get(f"/api/v1/analyze/{scan_id}", headers=_auth(stranger))
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "scan_not_found"


async def test_legacy_scan_returns_410_with_code(client, db_session):
    """LD-5 — tracker row exists but analysis_payload IS NULL."""
    user = await _seed_user(db_session)
    scan_id = await _seed_scan(db_session, user, with_payload=False)

    r = await client.get(f"/api/v1/analyze/{scan_id}", headers=_auth(user))
    assert r.status_code == 410
    detail = r.json()["detail"]
    assert detail["error"] == "scan_payload_unavailable"
    assert detail["code"] == "legacy_scan_pre_persistence"
    assert detail["scan_id"] == scan_id


async def test_owner_gets_full_payload_round_trip(client, db_session):
    """AC-2 — full AnalysisResponse returned; rich sub-objects intact."""
    user = await _seed_user(db_session)
    scan_id = await _seed_scan(db_session, user, with_payload=True)

    r = await client.get(f"/api/v1/analyze/{scan_id}", headers=_auth(user))
    assert r.status_code == 200
    body = r.json()
    assert body["scan_id"] == scan_id
    assert body["ats_score"] == 81
    assert body["grade"] == "A"
    assert body["score_breakdown"]["keyword_match"] == 80.0
    assert body["skill_gaps"][0]["skill"] == "Kubernetes"
    assert body["job_fit_explanation"] == "Strong alignment on backend stack."


async def test_list_tracker_response_omits_analysis_payload(client, db_session):
    """AC-3 — LD-2 deferred() keeps GET /tracker list responses small.
    The `analysis_payload` key must NOT appear in the tracker list envelope."""
    user = await _seed_user(db_session)
    await _seed_scan(db_session, user, with_payload=True)

    r = await client.get("/api/v1/tracker", headers=_auth(user))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    for row in rows:
        assert "analysis_payload" not in row, (
            "deferred() load must keep analysis_payload out of the list envelope"
        )
