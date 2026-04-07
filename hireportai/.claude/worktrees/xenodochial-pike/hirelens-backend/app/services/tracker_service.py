"""SQLite-backed job application tracker service."""
import uuid
from datetime import datetime
from typing import List, Optional

import aiosqlite

from app.db.database import DB_PATH
from app.models.request_models import TrackerApplicationCreate, TrackerApplicationUpdate
from app.models.response_models import TrackerApplication


async def create_application(data: TrackerApplicationCreate) -> TrackerApplication:
    """Create a new job application in the tracker.

    Args:
        data: Application creation data.

    Returns:
        The created TrackerApplication.
    """
    app_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO tracker_applications (id, company, role, date_applied, ats_score, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (app_id, data.company, data.role, data.date_applied, data.ats_score, data.status, created_at),
        )
        await db.commit()

    return TrackerApplication(
        id=app_id,
        company=data.company,
        role=data.role,
        date_applied=data.date_applied,
        ats_score=data.ats_score,
        status=data.status,
        created_at=created_at,
    )


async def get_applications() -> List[TrackerApplication]:
    """Get all job applications from the tracker.

    Returns:
        List of TrackerApplication objects sorted by created_at descending.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tracker_applications ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()

    return [
        TrackerApplication(
            id=row["id"],
            company=row["company"],
            role=row["role"],
            date_applied=row["date_applied"],
            ats_score=row["ats_score"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def get_application_by_id(app_id: str) -> Optional[TrackerApplication]:
    """Get a single application by ID.

    Args:
        app_id: The application UUID.

    Returns:
        TrackerApplication or None if not found.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tracker_applications WHERE id = ?", (app_id,)
        )
        row = await cursor.fetchone()

    if not row:
        return None

    return TrackerApplication(
        id=row["id"],
        company=row["company"],
        role=row["role"],
        date_applied=row["date_applied"],
        ats_score=row["ats_score"],
        status=row["status"],
        created_at=row["created_at"],
    )


async def update_application(
    app_id: str, data: TrackerApplicationUpdate
) -> Optional[TrackerApplication]:
    """Update an existing application.

    Args:
        app_id: The application UUID to update.
        data: Fields to update (None fields are skipped).

    Returns:
        Updated TrackerApplication or None if not found.
    """
    existing = await get_application_by_id(app_id)
    if not existing:
        return None

    # Build update dict from non-None fields
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return existing

    set_clauses = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [app_id]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE tracker_applications SET {set_clauses} WHERE id = ?",
            values,
        )
        await db.commit()

    return await get_application_by_id(app_id)


async def delete_application(app_id: str) -> bool:
    """Delete an application from the tracker.

    Args:
        app_id: The application UUID to delete.

    Returns:
        True if deleted, False if not found.
    """
    existing = await get_application_by_id(app_id)
    if not existing:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM tracker_applications WHERE id = ?", (app_id,)
        )
        await db.commit()

    return True
