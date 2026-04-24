"""Spec #59 — tracker_service_v2 scan payload + ownership unit tests.

Covers:
- `create_application` persists `analysis_payload` when provided; leaves
  NULL when the kwarg is omitted.
- `get_scan_by_id` returns the ORM row with `analysis_payload` materialized
  when the scan belongs to the requesting user.
- `get_scan_by_id` returns None (→ 404 at the route, LD-4) when the scan
  is owned by a different user — proves ownership leak is closed.
- `get_scan_by_id` returns None for unknown scan_id.
"""
from __future__ import annotations

import uuid

import pytest

from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate
from app.services.tracker_service_v2 import create_application, get_scan_by_id

pytestmark = pytest.mark.asyncio(loop_scope="session")


_SAMPLE_PAYLOAD = {
    "scan_id": "sample-scan-id",
    "ats_score": 72,
    "grade": "B",
    "score_breakdown": {
        "keyword_match": 75.0,
        "skills_coverage": 70.0,
        "formatting_compliance": 90.0,
        "bullet_strength": 65.0,
    },
    "matched_keywords": ["python", "fastapi"],
    "missing_keywords": ["kubernetes"],
    "skill_gaps": [
        {
            "skill": "Kubernetes",
            "category": "Technical",
            "importance": "critical",
        }
    ],
    "bullet_analysis": [],
    "formatting_issues": [],
    "job_fit_explanation": "Good match overall.",
    "top_strengths": ["python"],
    "top_gaps": ["kubernetes"],
    "keyword_chart_data": [],
    "skills_overlap_data": [],
    "resume_text": "Sample resume text.",
}


async def _seed_user(db_session, *, plan: str = "free") -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Scan Payload Test",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Subscription(user_id=user.id, plan=plan, status="active"))
    await db_session.flush()
    await db_session.refresh(user)
    return user


def _tracker_create(scan_id: str) -> TrackerApplicationCreate:
    return TrackerApplicationCreate(
        company="TestCorp",
        role="SWE",
        date_applied="2026-04-24",
        ats_score=72,
        status="Applied",
        scan_id=scan_id,
    )


async def test_create_application_persists_analysis_payload(db_session):
    user = await _seed_user(db_session)
    scan_id = str(uuid.uuid4())
    payload = {**_SAMPLE_PAYLOAD, "scan_id": scan_id}

    await create_application(
        _tracker_create(scan_id),
        db_session,
        user_id=user.id,
        analysis_payload=payload,
    )
    row = await get_scan_by_id(scan_id=scan_id, db=db_session, user_id=user.id)

    assert row is not None
    assert row.analysis_payload == payload


async def test_create_application_without_payload_leaves_null(db_session):
    user = await _seed_user(db_session)
    scan_id = str(uuid.uuid4())

    await create_application(
        _tracker_create(scan_id),
        db_session,
        user_id=user.id,
    )
    row = await get_scan_by_id(scan_id=scan_id, db=db_session, user_id=user.id)

    assert row is not None
    assert row.analysis_payload is None


async def test_get_scan_by_id_returns_none_for_cross_user(db_session):
    """LD-4 — ownership mismatch returns None → 404, not 403; don't leak."""
    owner = await _seed_user(db_session)
    stranger = await _seed_user(db_session)
    scan_id = str(uuid.uuid4())

    await create_application(
        _tracker_create(scan_id),
        db_session,
        user_id=owner.id,
        analysis_payload={**_SAMPLE_PAYLOAD, "scan_id": scan_id},
    )

    # Stranger requesting owner's scan — must return None (same shape as
    # unknown scan_id), so the route fires 404 with no existence-signal.
    result = await get_scan_by_id(
        scan_id=scan_id, db=db_session, user_id=stranger.id
    )
    assert result is None


async def test_get_scan_by_id_returns_none_for_unknown_id(db_session):
    user = await _seed_user(db_session)
    result = await get_scan_by_id(
        scan_id=str(uuid.uuid4()), db=db_session, user_id=user.id
    )
    assert result is None
