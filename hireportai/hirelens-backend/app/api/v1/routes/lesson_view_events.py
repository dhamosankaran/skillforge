"""Lesson view-event API route — Phase 6 slice 6.0 dual-write BE half.

Spec: docs/specs/phase-6/00-analytics-tables.md §6.3.

  POST /api/v1/lessons/{lesson_id}/view-event
    Auth: Depends(get_current_user)
    Body: LessonViewEventRequest
    Returns: 204 No Content (fire-and-forget from the FE)
    Errors: 401 unauthenticated; 404 lesson not found; 422 deck_id mismatch.

The FE's existing `capture('lesson_viewed', ...)` PostHog call at
`pages/Lesson.tsx:37` stays verbatim — this route writes the Postgres half
of the dual-write only (D-10 path (a)).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.lesson import Lesson
from app.models.user import User
from app.schemas.analytics_event import (
    LessonViewEventCreate,
    LessonViewEventRequest,
)
from app.services import analytics_event_service, quiz_item_study_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/lessons/{lesson_id}/view-event",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record a lesson view event (Postgres dual-write of FE `lesson_viewed`)",
)
async def post_lesson_view_event(
    lesson_id: str,
    body: LessonViewEventRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    lesson = (
        await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    ).scalar_one_or_none()
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    # Defensive — drift surfaces early per §6.3.
    if body.deck_id != lesson.deck_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="deck_id does not match lesson.deck_id",
        )

    plan = quiz_item_study_service._resolve_plan(user)
    persona = user.persona

    # D-7 best-effort wrapper — analytics never blocks the user request.
    try:
        await analytics_event_service.write_lesson_view_event(
            LessonViewEventCreate(
                user_id=user.id,
                lesson_id=lesson.id,
                deck_id=lesson.deck_id,
                version=body.version,
                session_id=body.session_id,
                plan=plan,
                persona=persona,
            ),
            db=db,
        )
    except Exception:
        logger.exception("lesson_view_event_dual_write_failed")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
