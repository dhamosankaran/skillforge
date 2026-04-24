"""Tests for spec #57 backend surface — tracker-level interview_date.

Covers:
- tracker_service_v2.create_application writes interview_date.
- Pydantic validators reject past dates and dates > 365 days out
  (HTTP 422 surface).
- tracker_service_v2.update_application sets and clears interview_date,
  honouring spec #57's PATCH semantics (explicit null clears; missing
  leaves unchanged).
- home_state_service.get_next_interview selection rule + tie-break +
  exclusion of terminal statuses + today/past handling.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.tracker import TrackerApplicationModel
from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate, TrackerApplicationUpdate
from app.services import home_state_service, tracker_service_v2

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _seed_user(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@tr-test.com",
        name="Tracker Test",
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token({"sub": user.id, "email": user.email})
    return user, token


async def _seed_tracker_row(
    db: AsyncSession,
    user_id: str,
    *,
    status: str = "Applied",
    interview_date: date | None = None,
    company: str = "Acme",
) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company=company,
        role="Engineer",
        date_applied=date.today().isoformat(),
        ats_score=0,
        status=status,
        interview_date=interview_date,
    )
    db.add(row)
    await db.flush()
    return row


# ── Pydantic validator tests ────────────────────────────────────────────────


async def test_interview_date_past_rejected_on_create():
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        TrackerApplicationCreate(
            company="X",
            role="Y",
            date_applied=date.today().isoformat(),
            interview_date=date.today() - timedelta(days=1),
        )
    assert "today or later" in str(exc_info.value)


async def test_interview_date_over_365_days_rejected_on_create():
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        TrackerApplicationCreate(
            company="X",
            role="Y",
            date_applied=date.today().isoformat(),
            interview_date=date.today() + timedelta(days=366),
        )
    assert "within 365 days" in str(exc_info.value)


async def test_interview_date_today_accepted_on_create():
    body = TrackerApplicationCreate(
        company="X",
        role="Y",
        date_applied=date.today().isoformat(),
        interview_date=date.today(),
    )
    assert body.interview_date == date.today()


async def test_interview_date_past_rejected_on_update():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TrackerApplicationUpdate(interview_date=date.today() - timedelta(days=1))


async def test_interview_date_null_allowed_on_update():
    """Explicit null is legal — it means "clear" in spec #57 PATCH semantics."""
    body = TrackerApplicationUpdate(interview_date=None)
    assert "interview_date" in body.model_fields_set


# ── Service tests ───────────────────────────────────────────────────────────


async def test_create_application_with_interview_date(db_session):
    user, _ = await _seed_user(db_session)
    iv_date = date.today() + timedelta(days=14)
    created = await tracker_service_v2.create_application(
        TrackerApplicationCreate(
            company="Google",
            role="SWE",
            date_applied=date.today().isoformat(),
            interview_date=iv_date,
        ),
        db_session,
        user_id=user.id,
    )
    assert created.interview_date == iv_date


async def test_update_application_sets_interview_date(db_session):
    user, _ = await _seed_user(db_session)
    row = await _seed_tracker_row(db_session, user.id)
    assert row.interview_date is None

    iv_date = date.today() + timedelta(days=7)
    updated = await tracker_service_v2.update_application(
        row.id,
        TrackerApplicationUpdate(interview_date=iv_date),
        db_session,
        user_id=user.id,
    )
    assert updated is not None
    assert updated.interview_date == iv_date


async def test_update_application_clears_interview_date_on_explicit_null(
    db_session,
):
    user, _ = await _seed_user(db_session)
    existing_date = date.today() + timedelta(days=3)
    row = await _seed_tracker_row(
        db_session, user.id, interview_date=existing_date
    )
    assert row.interview_date == existing_date

    updated = await tracker_service_v2.update_application(
        row.id,
        TrackerApplicationUpdate(interview_date=None),
        db_session,
        user_id=user.id,
    )
    assert updated is not None
    assert updated.interview_date is None


async def test_update_application_missing_field_leaves_date_unchanged(
    db_session,
):
    """PATCH with unrelated fields must not clear a previously-set date."""
    user, _ = await _seed_user(db_session)
    existing_date = date.today() + timedelta(days=3)
    row = await _seed_tracker_row(
        db_session, user.id, interview_date=existing_date
    )
    updated = await tracker_service_v2.update_application(
        row.id,
        TrackerApplicationUpdate(company="Updated"),
        db_session,
        user_id=user.id,
    )
    assert updated is not None
    assert updated.interview_date == existing_date


# ── home_state_service.get_next_interview ──────────────────────────────────


async def test_next_interview_picks_nearest_future_date(db_session):
    user, _ = await _seed_user(db_session)
    today = date.today()
    # Two future Applied rows: pick the nearer one.
    await _seed_tracker_row(
        db_session, user.id, interview_date=today + timedelta(days=14),
        company="FarCo",
    )
    await _seed_tracker_row(
        db_session, user.id, interview_date=today + timedelta(days=3),
        company="NearCo",
    )
    result = await home_state_service.get_next_interview(user.id, db_session)
    assert result is not None
    assert result.company == "NearCo"
    assert result.date == today + timedelta(days=3)


async def test_next_interview_null_when_no_future_dates(db_session):
    user, _ = await _seed_user(db_session)
    # A past interview_date is not selected; spec #57 AC-4 says >= today.
    await _seed_tracker_row(
        db_session, user.id, interview_date=date.today() - timedelta(days=1)
    )
    result = await home_state_service.get_next_interview(user.id, db_session)
    assert result is None


async def test_next_interview_excludes_rejected_and_offer(db_session):
    user, _ = await _seed_user(db_session)
    today = date.today()
    # Future dates but terminal statuses — excluded.
    await _seed_tracker_row(
        db_session, user.id, status="Rejected",
        interview_date=today + timedelta(days=3),
    )
    await _seed_tracker_row(
        db_session, user.id, status="Offer",
        interview_date=today + timedelta(days=5),
    )
    # Active row that should win.
    await _seed_tracker_row(
        db_session, user.id, status="Applied",
        interview_date=today + timedelta(days=10),
        company="LivePath",
    )
    result = await home_state_service.get_next_interview(user.id, db_session)
    assert result is not None
    assert result.company == "LivePath"


async def test_next_interview_today_handled_correctly(db_session):
    user, _ = await _seed_user(db_session)
    today = date.today()
    await _seed_tracker_row(
        db_session, user.id, interview_date=today, company="TodayCo"
    )
    result = await home_state_service.get_next_interview(user.id, db_session)
    assert result is not None
    assert result.date == today
    assert result.company == "TodayCo"


async def test_next_interview_ties_broken_by_created_at(db_session):
    user, _ = await _seed_user(db_session)
    same_date = date.today() + timedelta(days=5)
    earlier = await _seed_tracker_row(
        db_session, user.id, interview_date=same_date, company="First"
    )
    # Ensure second row has a later created_at.
    from datetime import datetime, timedelta as td
    earlier.created_at = datetime.now() - td(hours=2)
    await db_session.flush()
    await _seed_tracker_row(
        db_session, user.id, interview_date=same_date, company="Second"
    )
    result = await home_state_service.get_next_interview(user.id, db_session)
    assert result is not None
    assert result.company == "First"


async def test_next_interview_scoped_to_caller(db_session):
    user_a, _ = await _seed_user(db_session)
    user_b, _ = await _seed_user(db_session)
    today = date.today()
    await _seed_tracker_row(
        db_session, user_b.id, interview_date=today + timedelta(days=5),
        company="NotMine",
    )
    # user_a has nothing. user_b's row must not leak.
    result = await home_state_service.get_next_interview(user_a.id, db_session)
    assert result is None


# ── Route tests — validation + dual-write ──────────────────────────────────


async def test_patch_persona_dual_writes_tracker_when_eligible(
    client, db_session
):
    """Spec #57 §7.4 — persona update mirrors the date onto the user's
    most-recent active tracker row when that row's interview_date is null."""
    user, token = await _seed_user(db_session)
    await _seed_tracker_row(db_session, user.id, status="Applied")
    await db_session.commit()

    iv_date = (date.today() + timedelta(days=10)).isoformat()
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={
            "persona": "interview_prepper",
            "interview_target_date": iv_date,
            "interview_target_company": "Google",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # The tracker row should now carry the date too.
    from sqlalchemy import select
    row = (
        await db_session.execute(
            select(TrackerApplicationModel).where(
                TrackerApplicationModel.user_id == user.id
            )
        )
    ).scalar_one()
    assert row.interview_date == date.today() + timedelta(days=10)


async def test_patch_persona_never_overwrites_existing_tracker_date(
    client, db_session
):
    """Dual-write is a seed — if the tracker row already has a date, the
    persona endpoint must not clobber it."""
    user, token = await _seed_user(db_session)
    preset = date.today() + timedelta(days=5)
    await _seed_tracker_row(
        db_session, user.id, status="Applied", interview_date=preset
    )
    await db_session.commit()

    new_date = (date.today() + timedelta(days=20)).isoformat()
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={
            "persona": "interview_prepper",
            "interview_target_date": new_date,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    from sqlalchemy import select
    row = (
        await db_session.execute(
            select(TrackerApplicationModel).where(
                TrackerApplicationModel.user_id == user.id
            )
        )
    ).scalar_one()
    assert row.interview_date == preset  # untouched


async def test_patch_persona_no_tracker_row_is_best_effort(client, db_session):
    """With no active tracker row, persona PATCH still succeeds — dual-write
    is best-effort per spec AC-7 / prompt Step 4.3."""
    _, token = await _seed_user(db_session)
    iv_date = (date.today() + timedelta(days=7)).isoformat()
    resp = await client.patch(
        "/api/v1/users/me/persona",
        json={
            "persona": "interview_prepper",
            "interview_target_date": iv_date,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["interview_target_date"] == iv_date


async def test_tracker_post_rejects_past_date(client, db_session):
    """Route-surface validation — past date returns 422 (FastAPI's wrap of
    Pydantic ValueError). Spec AC-3."""
    _, token = await _seed_user(db_session)
    resp = await client.post(
        "/api/v1/tracker",
        json={
            "company": "X",
            "role": "Y",
            "date_applied": date.today().isoformat(),
            "interview_date": (
                date.today() - timedelta(days=1)
            ).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    locs = [
        ".".join(str(p) for p in err.get("loc", []))
        for err in resp.json()["detail"]
    ]
    assert any("interview_date" in loc for loc in locs)
