"""Admin authoring service for `lessons` (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §4.1.2 + §5.5-§5.8 +
§7 (substantive vs minor classification + retirement cascade) + §9.

Classification (`_is_substantive_change`) compares before/after of
`concept_md`, `production_md`, `examples_md` per §7.2 using
`difflib.SequenceMatcher` — stdlib, no new dep. The 0.15 threshold is
shared with the FE via `SUBSTANTIVE_EDIT_THRESHOLD` in `admin_errors`.
"""
from __future__ import annotations

import difflib
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.schemas.lesson import (
    AdminLessonStatusFilter,
    LessonCreateRequest,
    LessonResponse,
    LessonUpdateRequest,
    LessonUpdateResponse,
)
from app.services.admin_errors import (
    DeckNotFoundError,
    EditClassificationConflictError,
    LessonArchivedError,
    LessonNotFoundError,
    LessonSlugConflictError,
    SUBSTANTIVE_EDIT_THRESHOLD,
)


def _is_substantive_change(
    old: str, new: str, threshold: float = SUBSTANTIVE_EDIT_THRESHOLD
) -> bool:
    """Per §7.2 — >threshold normalized character-delta is substantive.

    Uses `difflib.SequenceMatcher.ratio()` (stdlib) so we don't pull a
    new dep. The metric is `1 - ratio` where ratio=1.0 means identical;
    a 15% threshold on `1 - ratio` matches the spec phrasing of "more
    than the threshold".
    """
    if old == new:
        return False
    ratio = difflib.SequenceMatcher(None, old, new).ratio()
    return (1.0 - ratio) > threshold


def _classify_lesson_edit(
    lesson: Lesson, payload: LessonUpdateRequest
) -> tuple[str, list[str]]:
    """Return (classification, fields_exceeding_threshold)."""
    fields_changed: list[str] = []
    if payload.concept_md is not None and _is_substantive_change(
        lesson.concept_md, payload.concept_md
    ):
        fields_changed.append("concept_md")
    if payload.production_md is not None and _is_substantive_change(
        lesson.production_md, payload.production_md
    ):
        fields_changed.append("production_md")
    if payload.examples_md is not None and _is_substantive_change(
        lesson.examples_md, payload.examples_md
    ):
        fields_changed.append("examples_md")
    classification = "substantive" if fields_changed else "minor"
    return classification, fields_changed


async def _fetch_lesson(lesson_id: str, db: AsyncSession) -> Lesson:
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise LessonNotFoundError(lesson_id)
    return lesson


async def _fetch_active_quiz_items(
    lesson_id: str, db: AsyncSession
) -> list[QuizItem]:
    result = await db.execute(
        select(QuizItem)
        .where(QuizItem.lesson_id == lesson_id)
        .where(QuizItem.retired_at.is_(None))
    )
    return list(result.scalars().all())


async def create_lesson(
    deck_id: str,
    payload: LessonCreateRequest,
    db: AsyncSession,
    admin_id: str,
) -> LessonResponse:
    """Create a lesson under a deck. 404 on missing deck, 409 on slug conflict."""
    deck_result = await db.execute(select(Deck).where(Deck.id == deck_id))
    deck = deck_result.scalar_one_or_none()
    if deck is None:
        raise DeckNotFoundError(deck_id)

    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=payload.slug,
        title=payload.title,
        concept_md=payload.concept_md,
        production_md=payload.production_md,
        examples_md=payload.examples_md,
        display_order=payload.display_order,
        version=1,
        version_type="initial",
    )
    db.add(lesson)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise LessonSlugConflictError(f"{deck_id}/{payload.slug}") from exc
    await db.refresh(lesson)

    analytics_track(
        admin_id,
        "admin_lesson_created",
        {
            "admin_id": admin_id,
            "lesson_id": lesson.id,
            "deck_id": lesson.deck_id,
            "slug": lesson.slug,
            "internal": True,
        },
    )
    return LessonResponse.model_validate(lesson)


async def update_lesson(
    lesson_id: str,
    payload: LessonUpdateRequest,
    db: AsyncSession,
    admin_id: str,
) -> LessonUpdateResponse:
    """PATCH a lesson. Substantive edits cascade-retire active quiz_items.

    Per §7.1, BE re-validates `payload.edit_classification` against the
    §7.2 rule and raises 409 on disagreement.
    """
    lesson = await _fetch_lesson(lesson_id, db)
    classification, threshold_fields = _classify_lesson_edit(lesson, payload)

    if classification != payload.edit_classification:
        raise EditClassificationConflictError(
            expected=classification,
            claimed=payload.edit_classification,
            fields=threshold_fields,
        )

    retired_ids: list[str] = []
    if classification == "substantive":
        for qi in await _fetch_active_quiz_items(lesson_id, db):
            qi.retired_at = func.now()
            retired_ids.append(qi.id)
        lesson.version += 1
        lesson.version_type = "substantive_edit"
    else:
        lesson.version_type = "minor_edit"

    fields_changed = []
    data = payload.model_dump(exclude_unset=True, exclude={"edit_classification"})
    for field, value in data.items():
        if value is None:
            continue
        if getattr(lesson, field) != value:
            setattr(lesson, field, value)
            fields_changed.append(field)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise LessonSlugConflictError(
            f"{lesson.deck_id}/{payload.slug or lesson.slug}"
        ) from exc
    await db.refresh(lesson)

    if classification == "substantive":
        analytics_track(
            admin_id,
            "admin_lesson_substantively_edited",
            {
                "admin_id": admin_id,
                "lesson_id": lesson.id,
                "deck_id": lesson.deck_id,
                "version": lesson.version,
                "prior_version": lesson.version - 1,
                "quiz_items_retired_count": len(retired_ids),
                "quiz_items_retired_ids": retired_ids,
                "internal": True,
            },
        )
        for qi_id in retired_ids:
            analytics_track(
                admin_id,
                "admin_quiz_item_retired",
                {
                    "admin_id": admin_id,
                    "quiz_item_id": qi_id,
                    "lesson_id": lesson.id,
                    "superseded_by_id": None,
                    "prior_version": 1,
                    "retire_reason": "lesson_substantive_cascade",
                    "internal": True,
                },
            )
    else:
        analytics_track(
            admin_id,
            "admin_lesson_updated_minor",
            {
                "admin_id": admin_id,
                "lesson_id": lesson.id,
                "deck_id": lesson.deck_id,
                "version": lesson.version,
                "fields_changed": fields_changed,
                "internal": True,
            },
        )

    return LessonUpdateResponse(
        lesson=LessonResponse.model_validate(lesson),
        version_type_applied=classification,
        quiz_items_retired_count=len(retired_ids),
        quiz_items_retired_ids=retired_ids,
    )


async def publish_lesson(
    lesson_id: str, db: AsyncSession, admin_id: str
) -> LessonResponse:
    """Flip `published_at` NULL → now(). 409 if archived. Idempotent."""
    lesson = await _fetch_lesson(lesson_id, db)
    if lesson.archived_at is not None:
        raise LessonArchivedError(lesson_id)
    if lesson.published_at is None:
        lesson.published_at = func.now()
        await db.flush()
        await db.refresh(lesson)
        analytics_track(
            admin_id,
            "admin_lesson_published",
            {
                "admin_id": admin_id,
                "lesson_id": lesson.id,
                "deck_id": lesson.deck_id,
                "version": lesson.version,
                "version_type": lesson.version_type,
                "generated_by_model": lesson.generated_by_model,
                "internal": True,
            },
        )
    return LessonResponse.model_validate(lesson)


async def archive_lesson(
    lesson_id: str, db: AsyncSession, admin_id: str
) -> LessonResponse:
    """Set `archived_at = now()`. Idempotent. Does NOT cascade-retire quiz_items."""
    lesson = await _fetch_lesson(lesson_id, db)
    if lesson.archived_at is None:
        was_published = lesson.published_at is not None
        lesson.archived_at = func.now()
        await db.flush()
        await db.refresh(lesson)
        analytics_track(
            admin_id,
            "admin_lesson_archived",
            {
                "admin_id": admin_id,
                "lesson_id": lesson.id,
                "deck_id": lesson.deck_id,
                "was_published": was_published,
                "internal": True,
            },
        )
    return LessonResponse.model_validate(lesson)


async def list_admin_lessons(
    deck_id: str,
    db: AsyncSession,
    status_filter: AdminLessonStatusFilter = "active",
) -> list[LessonResponse]:
    """List lessons under a deck with status filter (D-16)."""
    deck_check = await db.execute(select(Deck.id).where(Deck.id == deck_id))
    if deck_check.scalar_one_or_none() is None:
        raise DeckNotFoundError(deck_id)

    stmt = (
        select(Lesson)
        .where(Lesson.deck_id == deck_id)
        .order_by(Lesson.display_order.asc(), Lesson.created_at.asc())
    )
    if status_filter == "active":
        stmt = stmt.where(Lesson.archived_at.is_(None))
    elif status_filter == "drafts":
        stmt = stmt.where(Lesson.archived_at.is_(None)).where(
            Lesson.published_at.is_(None)
        )
    elif status_filter == "published":
        stmt = stmt.where(Lesson.archived_at.is_(None)).where(
            Lesson.published_at.is_not(None)
        )
    elif status_filter == "archived":
        stmt = stmt.where(Lesson.archived_at.is_not(None))
    # 'all' applies no filter

    result = await db.execute(stmt)
    return [LessonResponse.model_validate(l) for l in result.scalars().all()]
