"""SQLAlchemy-backed job application tracker service (v2)."""
import json
import uuid
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.models.tracker import TrackerApplicationModel
from app.schemas.requests import TrackerApplicationCreate, TrackerApplicationUpdate
from app.schemas.responses import TrackerApplication


def _require_user_id(user_id: str) -> None:
    """Reject calls that would operate across every tenant.

    Every read/write in this service is tenant-scoped. A None user_id
    would silently produce cross-tenant results; fail fast instead.
    """
    if user_id is None:
        raise ValueError("user_id is required; tracker_service_v2 is tenant-scoped")


def _to_response(model: TrackerApplicationModel) -> TrackerApplication:
    """Convert ORM model to Pydantic response."""
    matched = None
    missing = None
    if model.skills_matched:
        try:
            matched = json.loads(model.skills_matched)
        except (json.JSONDecodeError, TypeError):
            pass
    if model.skills_missing:
        try:
            missing = json.loads(model.skills_missing)
        except (json.JSONDecodeError, TypeError):
            pass

    return TrackerApplication(
        id=model.id,
        company=model.company,
        role=model.role,
        date_applied=model.date_applied,
        ats_score=model.ats_score,
        status=model.status,
        scan_id=model.scan_id,
        skills_matched=matched,
        skills_missing=missing,
        interview_date=model.interview_date,
        created_at=str(model.created_at),
    )


async def create_application(
    data: TrackerApplicationCreate,
    db: AsyncSession,
    user_id: str,
    skills_matched: Optional[List[str]] = None,
    skills_missing: Optional[List[str]] = None,
    analysis_payload: Optional[dict[str, Any]] = None,
) -> TrackerApplication:
    """Create a new job application for the given user.

    Spec #59: `analysis_payload` persists the full AnalysisResponse for
    scan re-view. None for non-scan-originated rows (manual adds via the
    tracker page).
    """
    _require_user_id(user_id)
    app = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company=data.company,
        role=data.role,
        date_applied=data.date_applied,
        ats_score=data.ats_score,
        status=data.status,
        scan_id=data.scan_id,
        skills_matched=json.dumps(skills_matched) if skills_matched else None,
        skills_missing=json.dumps(skills_missing) if skills_missing else None,
        interview_date=data.interview_date,
        analysis_payload=analysis_payload,
    )
    db.add(app)
    await db.flush()
    return _to_response(app)


async def get_scan_by_id(
    scan_id: str,
    db: AsyncSession,
    user_id: str,
) -> Optional[TrackerApplicationModel]:
    """Return the ORM row for a scan owned by the current user.

    Spec #59 §8. Unlike the other readers in this service (which return
    the Pydantic `TrackerApplication` summary), this returns the ORM
    model so the route can access `analysis_payload` directly. Ownership
    is enforced by matching `user_id`; rows owned by other users return
    None (→ 404 at the route, not 403, per LD-4).
    """
    _require_user_id(user_id)
    stmt = (
        select(TrackerApplicationModel)
        .where(TrackerApplicationModel.scan_id == scan_id)
        .where(TrackerApplicationModel.user_id == user_id)
        .options(undefer(TrackerApplicationModel.analysis_payload))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_by_scan_id(
    scan_id: str,
    db: AsyncSession,
    user_id: str,
) -> Optional[TrackerApplication]:
    """Find a tracker entry by scan_id within the user's own rows."""
    _require_user_id(user_id)
    stmt = (
        select(TrackerApplicationModel)
        .where(TrackerApplicationModel.scan_id == scan_id)
        .where(TrackerApplicationModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    return _to_response(model) if model else None


async def get_applications(
    db: AsyncSession,
    user_id: str,
) -> List[TrackerApplication]:
    """List all applications owned by the given user."""
    _require_user_id(user_id)
    stmt = (
        select(TrackerApplicationModel)
        .where(TrackerApplicationModel.user_id == user_id)
        .order_by(TrackerApplicationModel.created_at.desc())
    )
    result = await db.execute(stmt)
    return [_to_response(row) for row in result.scalars().all()]


async def get_application_by_id(
    app_id: str,
    db: AsyncSession,
    user_id: str,
) -> Optional[TrackerApplication]:
    """Get a single application by ID within the user's own rows."""
    _require_user_id(user_id)
    stmt = (
        select(TrackerApplicationModel)
        .where(TrackerApplicationModel.id == app_id)
        .where(TrackerApplicationModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    return _to_response(model) if model else None


async def update_application(
    app_id: str,
    data: TrackerApplicationUpdate,
    db: AsyncSession,
    user_id: str,
) -> Optional[TrackerApplication]:
    """Update an existing application owned by the given user."""
    _require_user_id(user_id)
    stmt = (
        select(TrackerApplicationModel)
        .where(TrackerApplicationModel.id == app_id)
        .where(TrackerApplicationModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        return None

    updates = data.model_dump(exclude_none=True)
    # Spec #57: PATCH semantics differ for interview_date — an explicit
    # null clears the date, whereas other fields treat null as "absent."
    # Detect explicit null via model_fields_set and re-inject it.
    if (
        "interview_date" in data.model_fields_set
        and data.interview_date is None
    ):
        updates["interview_date"] = None
    for key, value in updates.items():
        setattr(model, key, value)

    return _to_response(model)


async def delete_application(
    app_id: str,
    db: AsyncSession,
    user_id: str,
) -> bool:
    """Delete an application owned by the given user. Returns True if deleted."""
    _require_user_id(user_id)
    stmt = (
        select(TrackerApplicationModel)
        .where(TrackerApplicationModel.id == app_id)
        .where(TrackerApplicationModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        return False

    await db.delete(model)
    return True
