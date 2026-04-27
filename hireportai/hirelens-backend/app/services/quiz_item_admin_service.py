"""Admin authoring service for `quiz_items` (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §4.1.3 + §5.9-§5.10 +
§7.4 (quiz-item-level substantive edit retire-and-replace) + §9.

Substantive PATCH on a quiz_item retires the old row + inserts a new
`version+1` replacement linked via `superseded_by_id` per D-18. Existing
`quiz_item_progress` rows pointing at the old row are preserved (slice
6.2 §4.6 D-4 history-preservation invariant).
"""
from __future__ import annotations

import difflib
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.schemas.quiz_item import (
    AdminQuizItemStatusFilter,
    QuizItemCreateRequest,
    QuizItemResponse,
    QuizItemUpdateRequest,
)
from app.services.admin_errors import (
    EditClassificationConflictError,
    LessonArchivedError,
    LessonNotFoundError,
    QuizItemNotFoundError,
    SUBSTANTIVE_EDIT_THRESHOLD,
)


def _is_substantive_change(
    old: str, new: str, threshold: float = SUBSTANTIVE_EDIT_THRESHOLD
) -> bool:
    if old == new:
        return False
    ratio = difflib.SequenceMatcher(None, old, new).ratio()
    return (1.0 - ratio) > threshold


def _classify_quiz_item_edit(
    qi: QuizItem, payload: QuizItemUpdateRequest
) -> tuple[str, list[str]]:
    """Classify a quiz_item PATCH per §7.

    Substantive when question/answer cross the §7.2 threshold OR when
    question_type / distractors structurally change. Display order +
    difficulty are minor by themselves.
    """
    fields_changed: list[str] = []
    if payload.question is not None and _is_substantive_change(qi.question, payload.question):
        fields_changed.append("question")
    if payload.answer is not None and _is_substantive_change(qi.answer, payload.answer):
        fields_changed.append("answer")
    if payload.question_type is not None and payload.question_type != qi.question_type:
        fields_changed.append("question_type")
    if payload.distractors is not None and payload.distractors != (qi.distractors or []):
        fields_changed.append("distractors")
    classification = "substantive" if fields_changed else "minor"
    return classification, fields_changed


async def _fetch_quiz_item(quiz_item_id: str, db: AsyncSession) -> QuizItem:
    result = await db.execute(select(QuizItem).where(QuizItem.id == quiz_item_id))
    qi = result.scalar_one_or_none()
    if qi is None:
        raise QuizItemNotFoundError(quiz_item_id)
    return qi


async def _fetch_lesson(lesson_id: str, db: AsyncSession) -> Lesson:
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise LessonNotFoundError(lesson_id)
    return lesson


async def create_quiz_item(
    lesson_id: str,
    payload: QuizItemCreateRequest,
    db: AsyncSession,
    admin_id: str,
) -> QuizItemResponse:
    """Create a quiz_item under a lesson. 404 missing lesson, 409 archived."""
    lesson = await _fetch_lesson(lesson_id, db)
    if lesson.archived_at is not None:
        raise LessonArchivedError(lesson_id)

    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        question=payload.question,
        answer=payload.answer,
        question_type=payload.question_type,
        distractors=list(payload.distractors) if payload.distractors else None,
        difficulty=payload.difficulty,
        display_order=payload.display_order,
        version=1,
    )
    db.add(qi)
    await db.flush()
    await db.refresh(qi)

    analytics_track(
        admin_id,
        "admin_quiz_item_created",
        {
            "admin_id": admin_id,
            "quiz_item_id": qi.id,
            "lesson_id": qi.lesson_id,
            "question_type": qi.question_type,
            "difficulty": qi.difficulty,
            "internal": True,
        },
    )
    return QuizItemResponse.model_validate(qi)


async def update_quiz_item(
    quiz_item_id: str,
    payload: QuizItemUpdateRequest,
    db: AsyncSession,
    admin_id: str,
) -> QuizItemResponse:
    """PATCH a quiz_item.

    - **Minor**: mutate in place, version unchanged.
    - **Substantive**: retire-and-replace per §7.4 / D-18 — insert new
      row with `version+1`, set `old.superseded_by_id`, set
      `old.retired_at`. Returns the NEW row's response.
    """
    old = await _fetch_quiz_item(quiz_item_id, db)
    classification, threshold_fields = _classify_quiz_item_edit(old, payload)

    if classification != payload.edit_classification:
        raise EditClassificationConflictError(
            expected=classification,
            claimed=payload.edit_classification,
            fields=threshold_fields,
        )

    if classification == "minor":
        data = payload.model_dump(
            exclude_unset=True, exclude={"edit_classification"}
        )
        for field, value in data.items():
            if value is None:
                continue
            setattr(old, field, value)
        await db.flush()
        await db.refresh(old)
        return QuizItemResponse.model_validate(old)

    # Substantive — retire-and-replace.
    new = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=old.lesson_id,
        question=payload.question if payload.question is not None else old.question,
        answer=payload.answer if payload.answer is not None else old.answer,
        question_type=(
            payload.question_type if payload.question_type is not None else old.question_type
        ),
        distractors=(
            list(payload.distractors)
            if payload.distractors is not None
            else (list(old.distractors) if old.distractors else None)
        ),
        difficulty=(
            payload.difficulty if payload.difficulty is not None else old.difficulty
        ),
        display_order=(
            payload.display_order
            if payload.display_order is not None
            else old.display_order
        ),
        version=old.version + 1,
    )
    db.add(new)
    await db.flush()
    await db.refresh(new)

    old.retired_at = func.now()
    old.superseded_by_id = new.id
    await db.flush()

    analytics_track(
        admin_id,
        "admin_quiz_item_created",
        {
            "admin_id": admin_id,
            "quiz_item_id": new.id,
            "lesson_id": new.lesson_id,
            "question_type": new.question_type,
            "difficulty": new.difficulty,
            "internal": True,
        },
    )
    analytics_track(
        admin_id,
        "admin_quiz_item_retired",
        {
            "admin_id": admin_id,
            "quiz_item_id": old.id,
            "lesson_id": old.lesson_id,
            "superseded_by_id": new.id,
            "prior_version": old.version,
            "retire_reason": "quiz_item_substantive_replace",
            "internal": True,
        },
    )
    return QuizItemResponse.model_validate(new)


async def retire_quiz_item(
    quiz_item_id: str,
    db: AsyncSession,
    admin_id: str,
    superseded_by_id: Optional[str] = None,
) -> QuizItemResponse:
    """Set `retired_at = now()`. Idempotent."""
    qi = await _fetch_quiz_item(quiz_item_id, db)
    if qi.retired_at is None:
        qi.retired_at = func.now()
        if superseded_by_id is not None:
            qi.superseded_by_id = superseded_by_id
        await db.flush()
        await db.refresh(qi)
        analytics_track(
            admin_id,
            "admin_quiz_item_retired",
            {
                "admin_id": admin_id,
                "quiz_item_id": qi.id,
                "lesson_id": qi.lesson_id,
                "superseded_by_id": superseded_by_id,
                "prior_version": qi.version,
                "retire_reason": "direct",
                "internal": True,
            },
        )
    return QuizItemResponse.model_validate(qi)


async def list_admin_quiz_items(
    lesson_id: str,
    db: AsyncSession,
    status_filter: AdminQuizItemStatusFilter = "active",
) -> list[QuizItemResponse]:
    """List quiz_items under a lesson with status filter (D-16)."""
    lesson_check = await db.execute(select(Lesson.id).where(Lesson.id == lesson_id))
    if lesson_check.scalar_one_or_none() is None:
        raise LessonNotFoundError(lesson_id)

    stmt = (
        select(QuizItem)
        .where(QuizItem.lesson_id == lesson_id)
        .order_by(QuizItem.display_order.asc(), QuizItem.created_at.asc())
    )
    if status_filter == "active":
        stmt = stmt.where(QuizItem.retired_at.is_(None))
    elif status_filter == "retired":
        stmt = stmt.where(QuizItem.retired_at.is_not(None))
    # 'all' applies no filter

    result = await db.execute(stmt)
    return [QuizItemResponse.model_validate(qi) for qi in result.scalars().all()]
