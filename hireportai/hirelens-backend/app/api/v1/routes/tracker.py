"""Job application tracker endpoint (v1) — SQLAlchemy + required auth."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate, TrackerApplicationUpdate
from app.schemas.rescan import ScoreHistoryResponse
from app.schemas.responses import TrackerApplication
from app.services import (
    home_state_service,
    tracker_application_score_service,
)
from app.services.tracker_service_v2 import (
    create_application,
    delete_application,
    get_application_model_by_id,
    get_applications,
    update_application,
)

router = APIRouter()


@router.get("/tracker", response_model=List[TrackerApplication])
async def list_applications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's job applications."""
    return await get_applications(db, user_id=user.id)


@router.post("/tracker", response_model=TrackerApplication, status_code=201)
async def create_app(
    body: TrackerApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a new job application for the current user."""
    result = await create_application(body, db, user_id=user.id)
    # Spec #57 §4.4 — bust the home-state cache whenever a tracker write
    # could change next_interview.
    home_state_service.invalidate(user.id)
    return result


@router.patch("/tracker/{app_id}", response_model=TrackerApplication)
async def update_app(
    app_id: str,
    body: TrackerApplicationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing job application owned by the current user."""
    result = await update_application(app_id, body, db, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")
    home_state_service.invalidate(user.id)
    return result


@router.delete("/tracker/{app_id}", status_code=204)
async def delete_app(
    app_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a job application owned by the current user."""
    deleted = await delete_application(app_id, db, user_id=user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")
    home_state_service.invalidate(user.id)


@router.get("/tracker/{app_id}/scores", response_model=ScoreHistoryResponse)
async def get_score_history(
    app_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoreHistoryResponse:
    """Return the full score history for a tracker application owned by
    the current user.

    Spec #63 (E-043) §6.4 — `<ScoreDeltaWidget>` read source. History is
    chronological (oldest-first) per §12 D-3 (no pagination v1; bounded
    to ~20 rows in practice). 404 when the row doesn't exist or is owned
    by another user (no row leak).
    """
    row = await get_application_model_by_id(app_id, db, user_id=user.id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")

    history = await tracker_application_score_service.get_score_history(
        tracker_application_id=app_id,
        user_id=user.id,
        db=db,
    )
    delta = tracker_application_score_service.compute_delta(history)
    return ScoreHistoryResponse(
        tracker_application_id=app_id,
        history=[
            tracker_application_score_service.to_history_entry(r) for r in history
        ],
        delta=delta,
    )
