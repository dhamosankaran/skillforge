"""tracker_application_score_service unit tests (E-043 / spec #63 §6.3).

Covers write_score_row + find_by_dedupe + get_score_history +
compute_delta + get_prior_overall_score + tenant scoping.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from app.models.response_models import (
    AnalysisResponse,
    ATSScoreBreakdown,
)
from app.models.subscription import Subscription
from app.models.tracker import TrackerApplicationModel
from app.models.tracker_application_score import TrackerApplicationScore
from app.models.user import User
from app.services import tracker_application_score_service as tas

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_user(db_session) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Score Test",
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
        scan_id=str(uuid.uuid4()),
        jd_text="Senior backend engineer with Python + FastAPI.",
        jd_hash="jd-hash-fixture",
    )
    db_session.add(row)
    await db_session.flush()
    return row


def _response(*, ats: int = 80, kw: float = 0.7) -> AnalysisResponse:
    return AnalysisResponse(
        scan_id=str(uuid.uuid4()),
        ats_score=ats,
        grade="B",
        score_breakdown=ATSScoreBreakdown(
            keyword_match=kw,
            skills_coverage=0.6,
            formatting_compliance=0.9,
            bullet_strength=0.5,
        ),
        matched_keywords=[],
        missing_keywords=[],
        skill_gaps=[],
        bullet_analysis=[],
        formatting_issues=[],
        job_fit_explanation="",
        top_strengths=[],
        top_gaps=[],
        keyword_chart_data=[],
        skills_overlap_data=[],
        resume_text="",
    )


async def test_write_score_row_persists_and_maps_breakdown(db_session):
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_id=user.id)

    row = await tas.write_score_row(
        tracker_application_id=tracker.id,
        user_id=user.id,
        response=_response(ats=84, kw=0.71),
        scan_id="scan-A",
        jd_hash="jh",
        resume_hash="rh",
        db=db_session,
    )

    assert row.id
    assert row.tracker_application_id == tracker.id
    assert row.user_id == user.id
    assert row.overall_score == 84
    assert row.keyword_match_score == pytest.approx(0.71)
    assert row.scan_id == "scan-A"


async def test_find_by_dedupe_returns_match_else_none(db_session):
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_id=user.id)

    await tas.write_score_row(
        tracker_application_id=tracker.id,
        user_id=user.id,
        response=_response(),
        scan_id="scan-1",
        jd_hash="JH",
        resume_hash="RH",
        db=db_session,
    )

    hit = await tas.find_by_dedupe(
        tracker_application_id=tracker.id,
        jd_hash="JH",
        resume_hash="RH",
        db=db_session,
    )
    miss = await tas.find_by_dedupe(
        tracker_application_id=tracker.id,
        jd_hash="JH",
        resume_hash="OTHER",
        db=db_session,
    )

    assert hit is not None
    assert hit.scan_id == "scan-1"
    assert miss is None


async def test_get_score_history_is_oldest_first_and_tenant_scoped(db_session):
    user_a = await _seed_user(db_session)
    user_b = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_id=user_a.id)

    base = datetime.now(timezone.utc) - timedelta(days=2)
    for i, when in enumerate([base, base + timedelta(days=1), base + timedelta(days=2)]):
        row = TrackerApplicationScore(
            tracker_application_id=tracker.id,
            user_id=user_a.id,
            scan_id=f"s-{i}",
            overall_score=70 + i,
            keyword_match_score=0.5 + i * 0.05,
            skills_coverage_score=0.6,
            formatting_compliance_score=0.9,
            bullet_strength_score=0.4,
            jd_hash="jh",
            resume_hash=f"rh-{i}",
            scanned_at=when,
        )
        db_session.add(row)
    await db_session.flush()

    history_a = await tas.get_score_history(
        tracker_application_id=tracker.id, user_id=user_a.id, db=db_session
    )
    history_b = await tas.get_score_history(
        tracker_application_id=tracker.id, user_id=user_b.id, db=db_session
    )

    assert [r.overall_score for r in history_a] == [70, 71, 72]
    assert history_b == []


async def test_compute_delta_none_when_history_lt_2(db_session: Optional[object] = None):
    """compute_delta is sync but pytestmark.asyncio applies module-wide;
    keep the coroutine signature so the warning stays quiet without
    splitting the file (matches `tests/services/test_analysis_service.py`
    convention of one pytestmark per module).
    """
    assert tas.compute_delta([]) is None
    one = TrackerApplicationScore(
        tracker_application_id="t",
        user_id="u",
        overall_score=50,
        keyword_match_score=0.0,
        skills_coverage_score=0.0,
        formatting_compliance_score=0.0,
        bullet_strength_score=0.0,
        jd_hash="x",
        resume_hash="y",
        scanned_at=datetime.now(timezone.utc),
    )
    assert tas.compute_delta([one]) is None


def _row(overall: int, kw: float, when: datetime, *, axis: float = 0.5) -> TrackerApplicationScore:
    return TrackerApplicationScore(
        tracker_application_id="t",
        user_id="u",
        overall_score=overall,
        keyword_match_score=kw,
        skills_coverage_score=axis,
        formatting_compliance_score=axis,
        bullet_strength_score=axis,
        jd_hash="x",
        resume_hash="y",
        scanned_at=when,
    )


async def test_compute_delta_uses_latest_two_only():
    base = datetime.now(timezone.utc) - timedelta(days=10)
    history = [
        _row(50, 0.3, base),
        _row(70, 0.5, base + timedelta(days=3)),
        _row(80, 0.6, base + timedelta(days=5)),
    ]
    delta = tas.compute_delta(history)
    assert delta is not None
    assert delta.overall_delta == 10  # 80 - 70 (latest two only)
    assert delta.keyword_match_delta == pytest.approx(0.1)
    assert delta.days_between == 2


async def test_get_prior_overall_score_returns_most_recent_before(db_session):
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_id=user.id)

    base = datetime.now(timezone.utc) - timedelta(days=5)
    for i, score in enumerate([60, 75, 85]):
        db_session.add(
            TrackerApplicationScore(
                tracker_application_id=tracker.id,
                user_id=user.id,
                scan_id=f"s-{i}",
                overall_score=score,
                keyword_match_score=0.0,
                skills_coverage_score=0.0,
                formatting_compliance_score=0.0,
                bullet_strength_score=0.0,
                jd_hash="jh",
                resume_hash=f"rh-{i}",
                scanned_at=base + timedelta(days=i),
            )
        )
    await db_session.flush()

    prior_before_latest = await tas.get_prior_overall_score(
        tracker_application_id=tracker.id,
        before=base + timedelta(days=2),
        db=db_session,
    )
    assert prior_before_latest == 75  # the row at base+1, most recent before base+2

    prior_before_oldest = await tas.get_prior_overall_score(
        tracker_application_id=tracker.id,
        before=base,
        db=db_session,
    )
    assert prior_before_oldest is None
