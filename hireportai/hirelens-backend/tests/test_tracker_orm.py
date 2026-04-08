"""Tracker ORM consolidation tests (post AC-3).

Verifies that ``tracker_service_v2`` is the single storage path for both
authenticated and unauthenticated tracker rows.

``loop_scope="session"`` is required so that test bodies share the same event
loop as the session-scoped ``engine`` / ``db_session`` fixtures in conftest.py.
Without it SQLAlchemy raises "Future attached to a different loop".
"""
import uuid

import pytest

from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate, TrackerApplicationUpdate
from app.services import tracker_service_v2

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _payload(**overrides):
    base = dict(
        company="Acme",
        role="Engineer",
        date_applied="2026-04-01",
        ats_score=87,
        status="Applied",
    )
    base.update(overrides)
    return TrackerApplicationCreate(**base)


async def test_unauthenticated_crud(db_session):
    created = await tracker_service_v2.create_application(
        _payload(company="NoAuthCo"), db_session, user_id=None
    )
    assert created.company == "NoAuthCo"

    listed = await tracker_service_v2.get_applications(db_session, user_id=None)
    assert any(a.id == created.id for a in listed)

    updated = await tracker_service_v2.update_application(
        created.id,
        TrackerApplicationUpdate(status="Interview"),
        db_session,
        user_id=None,
    )
    assert updated is not None and updated.status == "Interview"

    deleted = await tracker_service_v2.delete_application(
        created.id, db_session, user_id=None
    )
    assert deleted is True


async def test_authenticated_scoped_crud(db_session):
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Auth User",
    )
    db_session.add(user)
    await db_session.flush()

    created = await tracker_service_v2.create_application(
        _payload(company="AuthCo"), db_session, user_id=user.id
    )
    scoped = await tracker_service_v2.get_applications(db_session, user_id=user.id)
    assert any(a.id == created.id for a in scoped)

    # A different user must not see this row.
    other_id = str(uuid.uuid4())
    other_view = await tracker_service_v2.get_applications(db_session, user_id=other_id)
    assert not any(a.id == created.id for a in other_view)

    deleted = await tracker_service_v2.delete_application(
        created.id, db_session, user_id=user.id
    )
    assert deleted is True
