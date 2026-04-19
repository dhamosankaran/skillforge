"""Tracker ORM tenant-scoping contract (spec #45 — hardened from AC-3 precursor).

Verifies that ``tracker_service_v2`` is the single storage path for
authenticated tracker rows, enforces tenant scoping on reads *and* writes,
and refuses any call that would silently operate across every tenant.

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


# ---------------------------------------------------------------------------
# Null-user_id rejection — one test per service function (spec #45 §4 AC-3/4)
# ---------------------------------------------------------------------------
# The service previously accepted ``user_id=None`` and silently dropped the
# ``WHERE user_id = :uid`` filter, returning/mutating every tenant's rows.
# Each function now rejects None at runtime so a regression cannot land by
# accident — type tightening is a call-site signal, not a runtime guarantee.


async def test_create_application_rejects_null_user_id(db_session):
    with pytest.raises(ValueError, match="user_id"):
        await tracker_service_v2.create_application(
            _payload(company="NoAuthCo"), db_session, user_id=None
        )


async def test_find_by_scan_id_rejects_null_user_id(db_session):
    with pytest.raises(ValueError, match="user_id"):
        await tracker_service_v2.find_by_scan_id(
            "any-scan-id", db_session, user_id=None
        )


async def test_get_applications_rejects_null_user_id(db_session):
    with pytest.raises(ValueError, match="user_id"):
        await tracker_service_v2.get_applications(db_session, user_id=None)


async def test_get_application_by_id_rejects_null_user_id(db_session):
    with pytest.raises(ValueError, match="user_id"):
        await tracker_service_v2.get_application_by_id(
            "any-id", db_session, user_id=None
        )


async def test_update_application_rejects_null_user_id(db_session):
    with pytest.raises(ValueError, match="user_id"):
        await tracker_service_v2.update_application(
            "any-id",
            TrackerApplicationUpdate(status="Interview"),
            db_session,
            user_id=None,
        )


async def test_delete_application_rejects_null_user_id(db_session):
    with pytest.raises(ValueError, match="user_id"):
        await tracker_service_v2.delete_application(
            "any-id", db_session, user_id=None
        )
