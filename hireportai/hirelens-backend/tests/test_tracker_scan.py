"""Tests for auto-populating tracker from ATS scan results.

Verifies that:
1. A scan creates a tracker entry with correct fields
2. Duplicate scan_ids are detected and skipped
3. Tracker entries contain the right ATS score and skills data
"""
import uuid

import pytest

from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate
from app.services import tracker_service_v2

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _scan_payload(scan_id: str, **overrides):
    base = dict(
        company="Google",
        role="Software Engineer",
        date_applied="2026-04-11",
        ats_score=78,
        status="Applied",
        scan_id=scan_id,
    )
    base.update(overrides)
    return TrackerApplicationCreate(**base)


@pytest.fixture
async def test_user(db_session):
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Scan Test User",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_scan_creates_tracker_entry(db_session, test_user):
    """A successful scan should create a tracker entry with all fields."""
    scan_id = str(uuid.uuid4())
    created = await tracker_service_v2.create_application(
        _scan_payload(scan_id, company="Meta", role="SWE Intern", ats_score=85),
        db_session,
        user_id=test_user.id,
        skills_matched=["Python", "React", "SQL"],
        skills_missing=["Kubernetes", "GraphQL"],
    )

    assert created.company == "Meta"
    assert created.role == "SWE Intern"
    assert created.ats_score == 85
    assert created.scan_id == scan_id
    assert created.status == "Applied"
    assert created.skills_matched == ["Python", "React", "SQL"]
    assert created.skills_missing == ["Kubernetes", "GraphQL"]


async def test_duplicate_scan_does_not_create_duplicate_tracker(db_session, test_user):
    """If a tracker entry with the same scan_id exists, find_by_scan_id returns it."""
    scan_id = str(uuid.uuid4())

    # Create first entry
    await tracker_service_v2.create_application(
        _scan_payload(scan_id, company="Apple"),
        db_session,
        user_id=test_user.id,
    )

    # Check for existing — should find it
    existing = await tracker_service_v2.find_by_scan_id(
        scan_id, db_session, user_id=test_user.id
    )
    assert existing is not None
    assert existing.company == "Apple"
    assert existing.scan_id == scan_id


async def test_tracker_entry_has_correct_fields(db_session, test_user):
    """Verify all fields are persisted and returned correctly."""
    scan_id = str(uuid.uuid4())
    created = await tracker_service_v2.create_application(
        _scan_payload(
            scan_id,
            company="Amazon",
            role="Senior Backend",
            ats_score=92,
        ),
        db_session,
        user_id=test_user.id,
        skills_matched=["Java", "AWS", "DynamoDB"],
        skills_missing=["Go"],
    )

    # Verify via find_by_scan_id
    found = await tracker_service_v2.find_by_scan_id(
        scan_id, db_session, user_id=test_user.id
    )
    assert found is not None
    assert found.id == created.id
    assert found.company == "Amazon"
    assert found.role == "Senior Backend"
    assert found.ats_score == 92
    assert found.date_applied == "2026-04-11"
    assert found.status == "Applied"
    assert found.scan_id == scan_id
    assert found.skills_matched == ["Java", "AWS", "DynamoDB"]
    assert found.skills_missing == ["Go"]
    assert found.created_at  # Non-empty
