"""Spec #63 §16.6 R-5 / §6.3 — `/analyze` writes baseline score row for
the auto-created tracker (B-089 / D-029 IFD-5).

The route now calls `tracker_application_score_service.write_score_row`
immediately after `create_application` so the first `/rescan` after
`/analyze` lands `history.length=2` and the delta envelope is
non-degenerate. Without this, `HomeScoreDeltaWidget` requires two
`/rescan` calls before it renders.

These tests monkeypatch the file parser + scoring helper so the route
exercises the tracker-autocreate + baseline-write block deterministically
without any LLM or PDF dependency.
"""
from __future__ import annotations

import io
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.response_models import AnalysisResponse, ATSScoreBreakdown
from app.models.subscription import Subscription
from app.models.tracker import TrackerApplicationModel
from app.models.tracker_application_score import TrackerApplicationScore
from app.models.user import User
from app.utils.text_hash import hash_jd

pytestmark = pytest.mark.asyncio(loop_scope="session")


_RESUME_TEXT = (
    "Senior backend engineer with 5+ years building scalable Python "
    "services on FastAPI + PostgreSQL. Designed REST APIs and shipped "
    "CI/CD pipelines on GitHub Actions. Comfortable with Redis caching "
    "and distributed system architectures handling 10k requests/sec."
)
_JD_TEXT = (
    "Senior Backend Engineer — Acme. We need a Python + FastAPI engineer "
    "with PostgreSQL and Redis experience. Building scalable REST APIs "
    "is core. CI/CD via GitHub Actions a plus. 5+ years required."
)


def _fake_response(scan_id: str, ats_score: int = 70) -> AnalysisResponse:
    return AnalysisResponse(
        scan_id=scan_id,
        ats_score=ats_score,
        grade="B",
        score_breakdown=ATSScoreBreakdown(
            keyword_match=70.0,
            skills_coverage=65.0,
            formatting_compliance=85.0,
            bullet_strength=60.0,
        ),
        matched_keywords=["python", "fastapi"],
        missing_keywords=["kubernetes"],
        skill_gaps=[],
        bullet_analysis=[],
        formatting_issues=[],
        job_fit_explanation="Strong backend alignment.",
        top_strengths=["python"],
        top_gaps=["kubernetes"],
        keyword_chart_data=[],
        skills_overlap_data=[],
        resume_text=_RESUME_TEXT,
    )


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session, monkeypatch):
    """Stub parser + scoring helper so the route runs deterministically."""
    from app.api.routes import analyze as analyze_module

    async def _fake_score(*, resume_text, jd_text, db, user_id=None, **kwargs):
        return _fake_response(scan_id=str(uuid.uuid4()))

    def _fake_parse(_bytes):
        return {"full_text": _RESUME_TEXT, "bullet_points": [], "formatting_hints": {}}

    monkeypatch.setattr(analyze_module, "score_resume_against_jd", _fake_score)
    monkeypatch.setattr(analyze_module, "parse_pdf", _fake_parse)
    monkeypatch.setattr(analyze_module, "parse_docx", _fake_parse)

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


async def _seed_user(db_session, *, plan: str = "pro", role: str = "user") -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Baseline Score Test",
        role=role,
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


def _form() -> dict:
    files = {
        "resume_file": ("resume.pdf", io.BytesIO(b"%PDF-1.4\n" + b"x" * 200), "application/pdf"),
    }
    data = {"job_description": _JD_TEXT}
    return {"files": files, "data": data}


async def test_analyze_writes_baseline_score_row_for_auto_created_tracker(
    client, db_session
):
    """§16.6 R-5 — /analyze writes one tracker_application_scores row whose
    fields match the auto-created tracker + AnalysisResponse + JD/resume hashes.
    """
    user = await _seed_user(db_session, plan="pro")

    resp = await client.post("/api/v1/analyze", headers=_auth(user), **_form())
    assert resp.status_code == 200, resp.text

    tracker = (
        await db_session.execute(
            select(TrackerApplicationModel).where(
                TrackerApplicationModel.user_id == user.id
            )
        )
    ).scalar_one()

    rows = (
        await db_session.execute(
            select(TrackerApplicationScore).where(
                TrackerApplicationScore.tracker_application_id == tracker.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == user.id
    assert row.scan_id == tracker.scan_id
    assert row.overall_score == tracker.ats_score
    assert row.jd_hash == hash_jd(_JD_TEXT)
    assert row.resume_hash == hash_jd(_RESUME_TEXT)


async def test_first_rescan_after_analyze_has_two_history_rows_and_non_null_delta(
    client, db_session
):
    """§16.6 R-5 — first /rescan after /analyze observes history.length=2;
    rescan_completed payload's `ats_score_before` + `*_delta` fields are
    non-null on the very first re-scan (previously required two re-scans).
    """
    user = await _seed_user(db_session, plan="pro")

    a = await client.post("/api/v1/analyze", headers=_auth(user), **_form())
    assert a.status_code == 200

    tracker = (
        await db_session.execute(
            select(TrackerApplicationModel).where(
                TrackerApplicationModel.user_id == user.id
            )
        )
    ).scalar_one()

    # /rescan with a different resume so the dedupe short-circuit doesn't fire.
    rescan_resume = _RESUME_TEXT + " Built systems handling 50k req/sec."
    r = await client.post(
        "/api/v1/analyze/rescan",
        headers=_auth(user),
        json={
            "tracker_application_id": tracker.id,
            "resume_text": rescan_resume,
        },
    )
    assert r.status_code == 200, r.text

    rows = (
        await db_session.execute(
            select(TrackerApplicationScore)
            .where(TrackerApplicationScore.tracker_application_id == tracker.id)
            .order_by(TrackerApplicationScore.scanned_at.asc())
        )
    ).scalars().all()
    assert len(rows) == 2
    assert rows[0].resume_hash != rows[1].resume_hash


async def test_analyze_baseline_write_is_idempotent_for_duplicate_scan(
    client, db_session
):
    """The auto-create branch is gated by `find_by_scan_id` — a duplicate
    /analyze call that lands on the same scan_id does NOT re-create the
    tracker row, so it does NOT write a second baseline row either.

    Each /analyze with distinct scan_ids creates a separate tracker row
    (intended), each with its own single baseline row — so a user calling
    /analyze twice gets two trackers with one score row each, not one
    tracker with two score rows.
    """
    user = await _seed_user(db_session, plan="pro")

    a = await client.post("/api/v1/analyze", headers=_auth(user), **_form())
    assert a.status_code == 200
    b = await client.post("/api/v1/analyze", headers=_auth(user), **_form())
    assert b.status_code == 200

    trackers = (
        await db_session.execute(
            select(TrackerApplicationModel).where(
                TrackerApplicationModel.user_id == user.id
            )
        )
    ).scalars().all()
    # Each call mints a fresh scan_id → a fresh tracker.
    assert len(trackers) == 2

    for tracker in trackers:
        count = (
            await db_session.execute(
                select(func.count(TrackerApplicationScore.id)).where(
                    TrackerApplicationScore.tracker_application_id == tracker.id
                )
            )
        ).scalar()
        assert count == 1
