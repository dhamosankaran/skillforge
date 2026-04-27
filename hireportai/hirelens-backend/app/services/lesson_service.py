"""Lesson + deck service — slice 6.4b body swap (DB-backed).

Spec: docs/specs/phase-6/03-lesson-ux.md §4.2 + slice 6.4b's §4.2 body
swap (D-2 byte-identical response shapes; D-15 selectinload strategy).

The four function signatures stay byte-identical to the slice-6.3
fixture-backed shape. Bodies become DB queries with
`selectinload(Lesson.quiz_items)` per D-15 to bound N+1 risk on the
user-facing read path.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.schemas.deck import DeckLessonsResponse, DeckResponse
from app.schemas.lesson import (
    LessonResponse,
    LessonWithQuizzesResponse,
)
from app.schemas.quiz_item import QuizItemResponse


async def get_lesson_with_quizzes(
    lesson_id: str, db: AsyncSession
) -> LessonWithQuizzesResponse | None:
    """Bundle a published lesson with its ordered active quiz items.

    Returns `None` (route maps to 404) when the lesson is missing,
    archived, unpublished, or its parent deck is archived.
    """
    stmt = (
        select(Lesson)
        .options(
            selectinload(
                Lesson.quiz_items.and_(QuizItem.retired_at.is_(None))
            ),
            selectinload(Lesson.deck),
        )
        .where(Lesson.id == lesson_id)
        .where(Lesson.archived_at.is_(None))
        .where(Lesson.published_at.is_not(None))
    )
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()
    if lesson is None:
        return None
    deck = lesson.deck
    if deck is None or deck.archived_at is not None:
        return None
    quiz_items = sorted(
        lesson.quiz_items, key=lambda qi: (qi.display_order, qi.created_at)
    )
    return LessonWithQuizzesResponse(
        lesson=LessonResponse.model_validate(lesson),
        quiz_items=[QuizItemResponse.model_validate(qi) for qi in quiz_items],
        deck_id=deck.id,
        deck_slug=deck.slug,
        deck_title=deck.title,
    )


async def get_deck_with_meta(
    deck_id: str, db: AsyncSession
) -> DeckResponse | None:
    """Single non-archived deck or None."""
    stmt = (
        select(Deck)
        .where(Deck.id == deck_id)
        .where(Deck.archived_at.is_(None))
    )
    result = await db.execute(stmt)
    deck = result.scalar_one_or_none()
    if deck is None:
        return None
    return DeckResponse.model_validate(deck)


async def list_lessons_in_deck(
    deck_id: str, db: AsyncSession
) -> list[LessonResponse]:
    """Active published lessons for a deck. Returns [] if deck has none."""
    stmt = (
        select(Lesson)
        .where(Lesson.deck_id == deck_id)
        .where(Lesson.archived_at.is_(None))
        .where(Lesson.published_at.is_not(None))
        .order_by(Lesson.display_order.asc(), Lesson.created_at.asc())
    )
    result = await db.execute(stmt)
    return [LessonResponse.model_validate(l) for l in result.scalars().all()]


async def get_deck_lessons_bundle(
    deck_id: str, db: AsyncSession
) -> DeckLessonsResponse | None:
    """Bundle a deck with its ordered active lessons.

    Returns `None` when the deck is missing or archived. Empty `lessons`
    list when the deck exists but has no published lessons (200, not 404).
    """
    deck = await get_deck_with_meta(deck_id, db)
    if deck is None:
        return None
    return DeckLessonsResponse(
        deck=deck, lessons=await list_lessons_in_deck(deck_id, db)
    )
