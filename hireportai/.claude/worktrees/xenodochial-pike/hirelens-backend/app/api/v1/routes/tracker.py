"""Job application tracker endpoint (v1) — SQLAlchemy + optional auth."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate, TrackerApplicationUpdate
from app.schemas.responses import TrackerApplication
from app.services.tracker_service_v2 import (
    create_application,
    delete_application,
    get_applications,
    update_application,
)

router = APIRouter()


@router.get("/tracker", response_model=List[TrackerApplication])
async def list_applications(
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """List job applications. If authenticated, scoped to user."""
    return await get_applications(db, user_id=user.id if user else None)


@router.post("/tracker", response_model=TrackerApplication, status_code=201)
async def create_app(
    body: TrackerApplicationCreate,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Save a new job application."""
    return await create_application(body, db, user_id=user.id if user else None)


@router.patch("/tracker/{app_id}", response_model=TrackerApplication)
async def update_app(
    app_id: str,
    body: TrackerApplicationUpdate,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing job application."""
    result = await update_application(
        app_id, body, db, user_id=user.id if user else None
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")
    return result


@router.delete("/tracker/{app_id}", status_code=204)
async def delete_app(
    app_id: str,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Remove a job application."""
    deleted = await delete_application(
        app_id, db, user_id=user.id if user else None
    )
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")
