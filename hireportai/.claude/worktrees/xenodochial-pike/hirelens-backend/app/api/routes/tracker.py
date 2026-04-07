"""Job application tracker CRUD endpoints."""
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.request_models import TrackerApplicationCreate, TrackerApplicationUpdate
from app.models.response_models import TrackerApplication

router = APIRouter()


@router.get("/tracker", response_model=List[TrackerApplication])
async def list_applications() -> List[TrackerApplication]:
    """List all saved job applications."""
    from app.services.tracker_service import get_applications
    return await get_applications()


@router.post("/tracker", response_model=TrackerApplication, status_code=201)
async def create_application(body: TrackerApplicationCreate) -> TrackerApplication:
    """Save a new job application to the tracker."""
    from app.services.tracker_service import create_application
    return await create_application(body)


@router.patch("/tracker/{app_id}", response_model=TrackerApplication)
async def update_application(app_id: str, body: TrackerApplicationUpdate) -> TrackerApplication:
    """Update an existing job application."""
    from app.services.tracker_service import update_application
    result = await update_application(app_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")
    return result


@router.delete("/tracker/{app_id}", status_code=204)
async def delete_application(app_id: str) -> None:
    """Remove a job application from the tracker."""
    from app.services.tracker_service import delete_application
    deleted = await delete_application(app_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found.")
