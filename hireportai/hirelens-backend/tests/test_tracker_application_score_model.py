"""Smoke tests for the new TrackerApplicationScore model (B-086a / E-043).

Spec: docs/specs/phase-5/63-ats-rescan-loop.md §5.3 + §5.4 + §7.

Foundation slice — exercises the new ORM model + the two new
``tracker_applications_v2`` columns added by the bundled migration
(D-020 closure). The /rescan route handler + score-history GET that
exercise these end-to-end land in B-086b.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect, select

from app.models.tracker import TrackerApplicationModel
from app.models.tracker_application_score import TrackerApplicationScore
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _make_user_kwargs() -> dict:
    suffix = uuid.uuid4().hex[:12]
    return {
        "id": str(uuid.uuid4()),
        "google_id": f"g-{suffix}",
        "email": f"u-{suffix}@example.com",
        "name": "Test User",
    }


async def _make_user(db_session) -> User:
    user = User(**_make_user_kwargs())
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_tracker_row(db_session, user_id: str, **overrides) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company="Stripe",
        role="Software Engineer",
        date_applied="2026-04-30",
        ats_score=72,
        status="Applied",
        scan_id=str(uuid.uuid4()),
        jd_text=overrides.pop("jd_text", "Build payments infra at scale."),
        jd_hash=overrides.pop("jd_hash", "a" * 64),
    )
    for k, v in overrides.items():
        setattr(row, k, v)
    db_session.add(row)
    await db_session.flush()
    return row


async def test_tracker_jd_columns_present_on_orm_model(db_session):
    """D-020 closure — `jd_text` + `jd_hash` are addressable on the model."""
    user = await _make_user(db_session)
    row = await _make_tracker_row(
        db_session, user.id, jd_text="JD body here", jd_hash="b" * 64
    )
    assert row.jd_text == "JD body here"
    assert row.jd_hash == "b" * 64

    # Round-trip via select() to confirm column persistence (not just
    # in-memory attribute).
    fetched = (
        await db_session.execute(
            select(TrackerApplicationModel).where(TrackerApplicationModel.id == row.id)
        )
    ).scalar_one()
    assert fetched.jd_text == "JD body here"
    assert fetched.jd_hash == "b" * 64


async def test_tracker_jd_columns_nullable(db_session):
    """D-10 — pre-migration rows allowed to carry both NULL."""
    user = await _make_user(db_session)
    row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user.id,
        company="LegacyCo",
        role="Eng",
        date_applied="2026-04-30",
        ats_score=0,
        status="Applied",
        scan_id=None,
        jd_text=None,
        jd_hash=None,
    )
    db_session.add(row)
    await db_session.flush()
    assert row.jd_text is None
    assert row.jd_hash is None


async def test_tracker_application_score_insert_and_fetch(db_session):
    """Score row writes with all required fields + reads back unchanged."""
    user = await _make_user(db_session)
    tracker = await _make_tracker_row(db_session, user.id)

    score = TrackerApplicationScore(
        tracker_application_id=tracker.id,
        user_id=user.id,
        scan_id=tracker.scan_id,
        overall_score=84,
        keyword_match_score=0.81,
        skills_coverage_score=0.74,
        formatting_compliance_score=0.95,
        bullet_strength_score=0.62,
        jd_hash=tracker.jd_hash,
        resume_hash="c" * 64,
    )
    db_session.add(score)
    await db_session.flush()

    fetched = (
        await db_session.execute(
            select(TrackerApplicationScore).where(
                TrackerApplicationScore.id == score.id
            )
        )
    ).scalar_one()
    assert fetched.tracker_application_id == tracker.id
    assert fetched.user_id == user.id
    assert fetched.overall_score == 84
    assert fetched.keyword_match_score == pytest.approx(0.81)
    assert fetched.skills_coverage_score == pytest.approx(0.74)
    assert fetched.formatting_compliance_score == pytest.approx(0.95)
    assert fetched.bullet_strength_score == pytest.approx(0.62)
    assert fetched.jd_hash == tracker.jd_hash
    assert fetched.resume_hash == "c" * 64
    assert fetched.scanned_at is not None  # server_default fired


async def test_tracker_application_score_indexes_present(db_session):
    """All three §5.3 indexes land on the new table."""

    def _collect(conn):
        insp = inspect(conn)
        return {ix["name"] for ix in insp.get_indexes("tracker_application_scores")}

    async with db_session.bind.connect() as conn:
        index_names = await conn.run_sync(_collect)

    assert "ix_tas_tracker_app_scanned_at" in index_names
    assert "ix_tas_user_scanned_at" in index_names
    assert "ix_tas_dedupe_lookup" in index_names
