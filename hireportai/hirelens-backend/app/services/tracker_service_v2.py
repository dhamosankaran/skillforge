"""SQLAlchemy-backed job application tracker service (v2)."""
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracker import TrackerApplicationModel
from app.schemas.requests import TrackerApplicationCreate, TrackerApplicationUpdate
from app.schemas.responses import TrackerApplication


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
        created_at=str(model.created_at),
    )


async def create_application(
    data: TrackerApplicationCreate,
    db: AsyncSession,
    user_id: Optional[str] = None,
    skills_matched: Optional[List[str]] = None,
    skills_missing: Optional[List[str]] = None,
) -> TrackerApplication:
    """Create a new job application."""
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
    )
    db.add(app)
    await db.flush()
    return _to_response(app)


async def find_by_scan_id(
    scan_id: str,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> Optional[TrackerApplication]:
    """Find a tracker entry by scan_id."""
    stmt = select(TrackerApplicationModel).where(
        TrackerApplicationModel.scan_id == scan_id
    )
    if user_id:
        stmt = stmt.where(TrackerApplicationModel.user_id == user_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    return _to_response(model) if model else None


async def get_applications(
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> List[TrackerApplication]:
    """Get all applications, optionally filtered by user."""
    stmt = select(TrackerApplicationModel).order_by(TrackerApplicationModel.created_at.desc())
    if user_id:
        stmt = stmt.where(TrackerApplicationModel.user_id == user_id)
    result = await db.execute(stmt)
    return [_to_response(row) for row in result.scalars().all()]


async def get_application_by_id(
    app_id: str,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> Optional[TrackerApplication]:
    """Get a single application by ID."""
    stmt = select(TrackerApplicationModel).where(TrackerApplicationModel.id == app_id)
    if user_id:
        stmt = stmt.where(TrackerApplicationModel.user_id == user_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    return _to_response(model) if model else None


async def update_application(
    app_id: str,
    data: TrackerApplicationUpdate,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> Optional[TrackerApplication]:
    """Update an existing application."""
    stmt = select(TrackerApplicationModel).where(TrackerApplicationModel.id == app_id)
    if user_id:
        stmt = stmt.where(TrackerApplicationModel.user_id == user_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        return None

    updates = data.model_dump(exclude_none=True)
    for key, value in updates.items():
        setattr(model, key, value)

    return _to_response(model)


async def delete_application(
    app_id: str,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> bool:
    """Delete an application. Returns True if deleted."""
    stmt = select(TrackerApplicationModel).where(TrackerApplicationModel.id == app_id)
    if user_id:
        stmt = stmt.where(TrackerApplicationModel.user_id == user_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        return False

    await db.delete(model)
    return True
