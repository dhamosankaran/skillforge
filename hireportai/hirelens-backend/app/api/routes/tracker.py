"""Job application tracker CRUD endpoints (legacy /api/tracker).

Delegates to ``tracker_service_v2`` (SQLAlchemy ORM) so the legacy and v1
routes share a single storage path. This route is unauthenticated, so all
rows it creates have ``user_id IS NULL``.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.request_models import TrackerApplicationCreate, TrackerApplicationUpdate
from app.models.response_models import TrackerApplication
from app.services import tracker_service_v2

router = APIRouter()


@router.get("/tracker", response_model=List[TrackerApplication])
async def list_applications(
    db: AsyncSession = Depends(get_db),
) -> List[TrackerApplication]:
    """List all unauthenticated tracker rows."""
    return await tracker_service_v2.get_applications(db, user_id=None)


@router.post("/tracker", response_model=TrackerApplication, status_code=201)
async def create_application(
    body: TrackerApplicationCreate,
    db: AsyncSession = Depends(get_db),
) -> TrackerApplication:
    """Save a new job application to the tracker."""
    return await tracker_service_v2.create_application(body, db, user_id=None)


@router.patch("/tracker/{app_id}", response_model=TrackerApplication)
async def update_application(
    app_id: str,
    body: TrackerApplicationUpdate,
    db: AsyncSession = Depends(get_db),
) -> TrackerApplication:
    """Update an existing job application."""
    result = await tracker_service_v2.update_application(app_id, body, db, user_id=None)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")
    return result


@router.delete("/tracker/{app_id}", status_code=204)
async def delete_application(
    app_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a job application from the tracker."""
    deleted = await tracker_service_v2.delete_application(app_id, db, user_id=None)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")
