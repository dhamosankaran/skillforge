"""Phase 6 analytics event service — Postgres dual-write for `quiz_review_events`
and `lesson_view_events`.

Spec: docs/specs/phase-6/00-analytics-tables.md §6.1.

The service surface is intentionally minimal — only `write_*` functions, no
UPDATE / DELETE / archive paths. The append-only invariant (§4.4 + AC-10) is
enforced structurally rather than via Postgres trigger.

D-7 failure semantics: each write wraps its INSERT in `try/except
SQLAlchemyError`, logs via `logger.exception(...)` with an event-type tag,
and returns `None` on failure. Callers (`quiz_item_study_service.review_quiz_item`
and the `POST /api/v1/lessons/:id/view-event` route) layer their own
`try/except Exception` so analytics failure NEVER blocks the user request.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import LessonViewEvent, QuizReviewEvent
from app.schemas.analytics_event import (
    LessonViewEventCreate,
    QuizReviewEventCreate,
)

logger = logging.getLogger(__name__)


async def write_quiz_review_event(
    payload: QuizReviewEventCreate,
    db: AsyncSession,
) -> None:
    """Insert one row into `quiz_review_events`. Best-effort per D-7."""
    try:
        row = QuizReviewEvent(
            id=str(uuid.uuid4()),
            user_id=payload.user_id,
            quiz_item_id=payload.quiz_item_id,
            lesson_id=payload.lesson_id,
            deck_id=payload.deck_id,
            rating=payload.rating,
            fsrs_state_before=payload.fsrs_state_before,
            fsrs_state_after=payload.fsrs_state_after,
            reps=payload.reps,
            lapses=payload.lapses,
            time_spent_ms=payload.time_spent_ms,
            session_id=payload.session_id,
            plan=payload.plan,
            persona=payload.persona,
        )
        db.add(row)
        await db.flush()
    except SQLAlchemyError:
        logger.exception(
            "analytics_event_write_failed",
            extra={"event_type": "quiz_item_reviewed"},
        )
        return None


async def write_lesson_view_event(
    payload: LessonViewEventCreate,
    db: AsyncSession,
) -> None:
    """Insert one row into `lesson_view_events`. Best-effort per D-7."""
    try:
        row = LessonViewEvent(
            id=str(uuid.uuid4()),
            user_id=payload.user_id,
            lesson_id=payload.lesson_id,
            deck_id=payload.deck_id,
            version=payload.version,
            session_id=payload.session_id,
            plan=payload.plan,
            persona=payload.persona,
        )
        db.add(row)
        await db.flush()
    except SQLAlchemyError:
        logger.exception(
            "analytics_event_write_failed",
            extra={"event_type": "lesson_viewed"},
        )
        return None
