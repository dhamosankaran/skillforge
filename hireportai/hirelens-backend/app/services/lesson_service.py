"""Lesson + deck service — slice 6.3 (fixture-data, read-only).

Spec: docs/specs/phase-6/03-lesson-ux.md §4.2.

Thin wrapper over `app/data/lesson_fixtures.py`. The `db: AsyncSession`
parameter is a forward-compat affordance — slice 6.3 ignores it; slice
6.4 swaps the wrapper bodies to DB queries without touching route
handlers (D-4).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.data import lesson_fixtures
from app.schemas.deck import DeckLessonsResponse, DeckResponse
from app.schemas.lesson import LessonResponse, LessonWithQuizzesResponse


async def get_lesson_with_quizzes(
    lesson_id: str, db: AsyncSession
) -> LessonWithQuizzesResponse | None:
    """Bundle a lesson with its ordered active quiz items.

    Returns `None` when the lesson does not exist or is archived, OR
    when the parent deck cannot be resolved (impossible with on-disk
    fixtures but defensive for the slice 6.4 DB swap).
    """
    del db  # forward-compat affordance; slice 6.4 will use it.
    lesson = lesson_fixtures.get_lesson(lesson_id)
    if lesson is None:
        return None
    deck = lesson_fixtures.get_deck(lesson.deck_id)
    if deck is None:
        return None
    return LessonWithQuizzesResponse(
        lesson=lesson,
        quiz_items=lesson_fixtures.list_quiz_items(lesson_id),
        deck_id=deck.id,
        deck_slug=deck.slug,
        deck_title=deck.title,
    )


async def get_deck_with_meta(
    deck_id: str, db: AsyncSession
) -> DeckResponse | None:
    """Single non-archived deck or None."""
    del db
    return lesson_fixtures.get_deck(deck_id)


async def list_lessons_in_deck(
    deck_id: str, db: AsyncSession
) -> list[LessonResponse]:
    """Active lessons for a deck (route handler 404s when deck is missing)."""
    del db
    return lesson_fixtures.list_lessons(deck_id)


async def get_deck_lessons_bundle(
    deck_id: str, db: AsyncSession
) -> DeckLessonsResponse | None:
    """Bundle a deck with its ordered active lessons.

    Returns `None` when the deck does not exist or is archived. Empty
    `lessons` list when the deck exists but has zero lessons.
    """
    deck = await get_deck_with_meta(deck_id, db)
    if deck is None:
        return None
    return DeckLessonsResponse(
        deck=deck, lessons=await list_lessons_in_deck(deck_id, db)
    )
