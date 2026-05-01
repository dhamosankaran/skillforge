"""POST /api/v1/analyze/rescan route tests (E-043 / spec #63 §6.2).

Covers AC-1..AC-9, AC-11, AC-16 from §11. AC-12 lives in the alembic
round-trip integration test; AC-13/AC-14 are FE-side; AC-17 is in
tests/services/test_analysis_service.py.
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
from app.models.tracker import TrackerApplicationModel
from app.models.tracker_application_score import TrackerApplicationScore
from app.models.usage_log import UsageLog
from app.models.user import User
from app.utils.text_hash import hash_jd

pytestmark = pytest.mark.asyncio(loop_scope="session")


_RESUME_TEXT = (
    "Experienced backend engineer with 5+ years building scalable Python "
    "services. Led migrations from monolith to microservices on FastAPI + "
    "PostgreSQL. Designed REST APIs with OpenAPI specs, optimized p99 "
    "latency through query tuning, and shipped CI/CD pipelines on GitHub "
    "Actions. Comfortable with Redis caching and distributed system "
    "architectures handling 10k requests per second."
)
_RESUME_TEXT_2 = (
    "Senior backend engineer with deep Python and FastAPI expertise. "
    "Architected high-throughput REST APIs and microservices. Built CI/CD "
    "pipelines and reduced p99 latency by 50% through caching and query "
    "optimization. Led teams of 4+ engineers across projects involving "
    "Redis, Postgres, and distributed processing. Proven track record."
)
_JD_TEXT = (
    "Senior Backend Engineer — Stripe. We need a Python + FastAPI engineer "
    "with PostgreSQL and Redis experience. Building scalable REST APIs and "
    "microservices is core. CI/CD via GitHub Actions a plus."
)


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


async def _seed_user(db_session, *, plan: str = "free", role: str = "user") -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Rescan Test",
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Subscription(user_id=user.id, plan=plan, status="active"))
    await db_session.flush()
    await db_session.refresh(user)
    return user


async def _seed_tracker(
    db_session,
    *,
    user_id: str,
    jd_text: str | None = _JD_TEXT,
) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        user_id=user_id,
        company="Stripe",
        role="Backend",
        date_applied="2026-04-30",
        ats_score=0,
        status="Applied",
        scan_id=str(uuid.uuid4()),
        jd_text=jd_text,
        jd_hash=hash_jd(jd_text) if jd_text else None,
    )
    db_session.add(row)
    await db_session.flush()
    return row


def _auth(user: User) -> dict[str, str]:
    tok = create_access_token({"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {tok}"}


async def test_rescan_unauthed_returns_401(client):
    """AC-1 — anonymous POST is rejected before any DB read."""
    resp = await client.post(
        "/api/v1/analyze/rescan",
        json={
            "tracker_application_id": "irrelevant",
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 401


async def test_rescan_other_users_tracker_returns_404(client, db_session):
    """AC-2 — cross-user tracker access does not leak existence (404)."""
    owner = await _seed_user(db_session, plan="pro")
    tracker = await _seed_tracker(db_session, user_id=owner.id)
    intruder = await _seed_user(db_session, plan="pro")

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(intruder),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 404


async def test_rescan_null_jd_text_returns_422_with_explicit_copy(
    client, db_session
):
    """AC-3 — pre-migration row with jd_text=NULL → 422 + explicit copy."""
    user = await _seed_user(db_session, plan="pro")
    tracker = await _seed_tracker(db_session, user_id=user.id, jd_text=None)

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "jd_text_missing"
    assert "fresh scan" in detail["message"].lower()


async def test_rescan_happy_path_writes_score_row_and_updates_tracker(
    client, db_session
):
    """AC-4 — first scan: 200 + score row written + ats_score updated."""
    user = await _seed_user(db_session, plan="pro")
    tracker = await _seed_tracker(db_session, user_id=user.id)

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["ats_score"], int)
    assert "score_breakdown" in body

    # Score row written
    from sqlalchemy import select

    rows = (
        await db_session.execute(
            select(TrackerApplicationScore).where(
                TrackerApplicationScore.tracker_application_id == tracker.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    written = rows[0]
    assert written.overall_score == body["ats_score"]
    assert written.keyword_match_score is not None
    assert written.skills_coverage_score is not None
    assert written.formatting_compliance_score is not None
    assert written.bullet_strength_score is not None
    assert written.jd_hash == tracker.jd_hash

    # Tracker row's ats_score flipped to the new score
    await db_session.refresh(tracker)
    assert tracker.ats_score == body["ats_score"]
    # Original scan_id is preserved per AC-9 invariant
    assert tracker.scan_id is not None


async def test_rescan_short_circuit_no_counter_increment(client, db_session):
    """AC-5 / D-2 — repeat call with same hashes returns existing scores
    without writing a new row and without consuming the counter.
    """
    user = await _seed_user(db_session, plan="free")
    tracker = await _seed_tracker(db_session, user_id=user.id)

    first = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert first.status_code == 200

    # Free user already at limit — but second call with identical hashes
    # should short-circuit before the counter is checked.
    second = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["ats_score"] == first.json()["ats_score"]

    from sqlalchemy import func, select

    score_count = (
        await db_session.execute(
            select(func.count(TrackerApplicationScore.id)).where(
                TrackerApplicationScore.tracker_application_id == tracker.id
            )
        )
    ).scalar()
    assert score_count == 1  # short-circuit did not write a new row

    usage_count = (
        await db_session.execute(
            select(func.count(UsageLog.id)).where(
                UsageLog.user_id == user.id
            ).where(UsageLog.feature_used == "analyze")
        )
    ).scalar()
    assert usage_count == 1  # only the first call consumed the counter


async def test_rescan_free_user_at_cap_gets_402_with_scan_limit_trigger(
    client, db_session
):
    """AC-6 — free user at lifetime cap → 402 with `trigger='scan_limit'`."""
    user = await _seed_user(db_session, plan="free")
    tracker = await _seed_tracker(db_session, user_id=user.id)
    db_session.add(
        UsageLog(user_id=user.id, feature_used="analyze", tokens_consumed=0)
    )
    await db_session.flush()

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 402
    detail = resp.json()["detail"]
    assert detail["error"] == "free_tier_limit"
    assert detail["trigger"] == "scan_limit"
    assert detail["plan"] == "free"


async def test_rescan_admin_bypasses_cap(client, db_session):
    """AC-7 — admin role bypass; counter never gates."""
    user = await _seed_user(db_session, plan="free", role="admin")
    tracker = await _seed_tracker(db_session, user_id=user.id)
    db_session.add(
        UsageLog(user_id=user.id, feature_used="analyze", tokens_consumed=0)
    )
    await db_session.flush()

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 200, resp.text


async def test_rescan_second_resume_creates_second_history_row(
    client, db_session
):
    """AC-4 + AC-9 — different resume hash → new score row, scan_id preserved."""
    user = await _seed_user(db_session, plan="pro")
    tracker = await _seed_tracker(db_session, user_id=user.id)
    original_scan_id = tracker.scan_id

    a = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert a.status_code == 200

    b = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT_2,
        },
    )
    assert b.status_code == 200

    from sqlalchemy import select

    rows = (
        await db_session.execute(
            select(TrackerApplicationScore)
            .where(
                TrackerApplicationScore.tracker_application_id == tracker.id
            )
            .order_by(TrackerApplicationScore.scanned_at.asc())
        )
    ).scalars().all()
    assert len(rows) == 2
    assert rows[0].resume_hash != rows[1].resume_hash

    await db_session.refresh(tracker)
    assert tracker.scan_id == original_scan_id  # AC-9


# ── B-088 / spec #63 §16.1 R-1 + §16.2 R-2 — rescan_failed + jd_hash_prefix ──
#
# These tests capture analytics_track calls via monkeypatch, mirroring the
# canonical pattern from tests/test_wall.py:174-181 (`captured_events`
# fixture). Patch target is the local import alias inside analyze.py
# (`app.api.routes.analyze.analytics_track`), not `app.core.analytics.track`,
# because the route module imported the symbol at module-load time.


@pytest.fixture
def captured_events(monkeypatch):
    """Capture every analytics_track call inside analyze.py route module."""
    from app.api.routes import analyze as analyze_module

    captured: list[tuple] = []

    def _capture(user_id, event, properties=None):
        captured.append((user_id, event, properties))

    monkeypatch.setattr(analyze_module, "analytics_track", _capture)
    return captured


async def test_rescan_404_fires_rescan_failed_with_not_found(
    client, db_session, captured_events
):
    """B-088 / §16.1 R-1 — 404 path fires `rescan_failed{not_found}`."""
    owner = await _seed_user(db_session, plan="pro")
    tracker = await _seed_tracker(db_session, user_id=owner.id)
    intruder = await _seed_user(db_session, plan="pro")

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(intruder),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 404

    failed = [
        props for (_uid, ev, props) in captured_events
        if ev == "rescan_failed"
    ]
    assert len(failed) == 1
    assert failed[0]["error_class"] == "not_found"
    assert failed[0]["tracker_application_id"] == tracker.id


async def test_rescan_422_fires_rescan_failed_with_jd_missing(
    client, db_session, captured_events
):
    """B-088 / §16.1 R-1 — 422 jd_text=NULL path fires `rescan_failed{jd_missing}`."""
    user = await _seed_user(db_session, plan="pro")
    tracker = await _seed_tracker(db_session, user_id=user.id, jd_text=None)

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 422

    failed = [
        props for (_uid, ev, props) in captured_events
        if ev == "rescan_failed"
    ]
    assert len(failed) == 1
    assert failed[0]["error_class"] == "jd_missing"
    assert failed[0]["tracker_application_id"] == tracker.id


async def test_rescan_402_fires_rescan_failed_with_paywall(
    client, db_session, captured_events
):
    """B-088 / §16.1 R-1 — 402 paywall path fires `rescan_failed{paywall}`."""
    user = await _seed_user(db_session, plan="free")
    tracker = await _seed_tracker(db_session, user_id=user.id)
    db_session.add(
        UsageLog(user_id=user.id, feature_used="analyze", tokens_consumed=0)
    )
    await db_session.flush()

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 402

    failed = [
        props for (_uid, ev, props) in captured_events
        if ev == "rescan_failed"
    ]
    assert len(failed) == 1
    assert failed[0]["error_class"] == "paywall"
    assert failed[0]["tracker_application_id"] == tracker.id


async def test_rescan_completed_payload_uses_jd_hash_prefix(
    client, db_session, captured_events
):
    """B-088 / §16.2 R-2 — `rescan_completed` payload uses 8-char `jd_hash_prefix`."""
    user = await _seed_user(db_session, plan="pro")
    tracker = await _seed_tracker(db_session, user_id=user.id)

    resp = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": _RESUME_TEXT,
        },
    )
    assert resp.status_code == 200, resp.text

    completed = [
        props for (_uid, ev, props) in captured_events
        if ev == "rescan_completed"
    ]
    assert len(completed) == 1
    payload = completed[0]
    assert "jd_hash_prefix" in payload
    assert "jd_hash" not in payload, (
        "full jd_hash must not be emitted post-§16.2 R-2"
    )
    assert len(payload["jd_hash_prefix"]) == 8
    # Prefix is the first 8 chars of the SHA-256 hex of the JD text.
    expected_prefix = hash_jd(_JD_TEXT)[:8]
    assert payload["jd_hash_prefix"] == expected_prefix
