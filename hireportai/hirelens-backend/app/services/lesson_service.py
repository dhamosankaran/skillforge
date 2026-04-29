"""Lesson + deck service — slice 6.4b body swap (DB-backed) + slice 6.5
read-time invariants.

Spec: docs/specs/phase-6/03-lesson-ux.md §4.2 + slice 6.4b's §4.2 body
swap (D-2 byte-identical response shapes; D-15 selectinload strategy);
slice 6.5 (`docs/specs/phase-6/06-read-time-invariants.md`) §6.2 +
§12 D-2 / D-3 / D-5 / D-7 / D-10.

Slice 6.5 adds a keyword-only ``user`` parameter on the four public
functions. SQL queries gain ``Deck.persona_visibility.in_(...)``
filters per D-3 (returns None / [] → 404 per D-7); ``list_lessons_in_deck``
also gains the defense-in-depth ``Deck.archived_at IS NULL`` filter
(§4.3 note ³). Tier mismatch raises ``QuizItemForbiddenError`` with
``reason='premium_deck'`` per D-2 / D-10 (route maps to 403).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.user import User
from app.schemas.deck import DeckLessonsResponse, DeckResponse
from app.schemas.lesson import (
    LessonResponse,
    LessonWithQuizzesResponse,
)
from app.schemas.quiz_item import QuizItemResponse
from app.services.curriculum_visibility import (
    _allowed_tiers_for_user,
    _persona_visible_to,
    _resolve_plan,
    _visible_persona_set,
)
from app.services.quiz_item_study_service import QuizItemForbiddenError


# ── Public service methods ───────────────────────────────────────────────────


async def get_lesson_with_quizzes(
    lesson_id: str,
    db: AsyncSession,
    *,
    user: Optional[User] = None,
) -> LessonWithQuizzesResponse | None:
    """Bundle a published lesson with its ordered active quiz items.

    Returns ``None`` (route maps to 404) when the lesson is missing,
    archived, unpublished, or its parent deck is archived OR not visible
    to the requesting user's persona (D-3 / D-7). Raises
    ``QuizItemForbiddenError`` (route → 403) when the parent deck is
    premium-tier and the user is on the free plan (D-2 / D-10).
    """
    visible_personas = _visible_persona_set(user)
    stmt = (
        select(Lesson)
        .options(
            selectinload(
                Lesson.quiz_items.and_(QuizItem.retired_at.is_(None))
            ),
            selectinload(Lesson.deck),
        )
        .join(Deck, Deck.id == Lesson.deck_id)
        .where(Lesson.id == lesson_id)
        .where(Lesson.archived_at.is_(None))
        .where(Lesson.published_at.is_not(None))
        .where(Deck.persona_visibility.in_(visible_personas))
    )
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()
    if lesson is None:
        return None
    deck = lesson.deck
    if deck is None or deck.archived_at is not None:
        return None
    if deck.tier not in _allowed_tiers_for_user(user):
        raise QuizItemForbiddenError(lesson_id, reason="premium_deck")
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
    deck_id: str,
    db: AsyncSession,
    *,
    user: Optional[User] = None,
) -> DeckResponse | None:
    """Single non-archived deck visible to the user, or None.

    Raises ``QuizItemForbiddenError`` (route → 403) when the deck is
    premium-tier and the user is on the free plan (D-2 / D-10).
    """
    visible_personas = _visible_persona_set(user)
    stmt = (
        select(Deck)
        .where(Deck.id == deck_id)
        .where(Deck.archived_at.is_(None))
        .where(Deck.persona_visibility.in_(visible_personas))
    )
    result = await db.execute(stmt)
    deck = result.scalar_one_or_none()
    if deck is None:
        return None
    if deck.tier not in _allowed_tiers_for_user(user):
        raise QuizItemForbiddenError(deck_id, reason="premium_deck")
    return DeckResponse.model_validate(deck)


async def list_lessons_in_deck(
    deck_id: str,
    db: AsyncSession,
    *,
    user: Optional[User] = None,
) -> list[LessonResponse]:
    """Active published lessons for a deck. Returns [] if the deck is
    archived, persona-narrowed away, or has no published lessons.

    Raises ``QuizItemForbiddenError`` (route → 403) when the deck is
    premium-tier and the user is on the free plan (D-2 / D-10).

    Slice 6.5 §4.3 note ³: the explicit ``Deck.archived_at IS NULL``
    filter is defense-in-depth — current callers front this through
    ``get_deck_with_meta``, but a direct caller (e.g. slice 6.6 ranker)
    would otherwise leak archived-deck lessons.
    """
    visible_personas = _visible_persona_set(user)
    # Tier check — only raises 403 if the deck is otherwise visible (not
    # archived, not persona-narrowed). Archive / persona mismatch take
    # priority and surface as [] (route → 404 at the call site if it
    # cared, or 200 with empty list otherwise).
    visible_deck = (
        await db.execute(
            select(Deck)
            .where(Deck.id == deck_id)
            .where(Deck.archived_at.is_(None))
            .where(Deck.persona_visibility.in_(visible_personas))
        )
    ).scalar_one_or_none()
    if (
        visible_deck is not None
        and visible_deck.tier not in _allowed_tiers_for_user(user)
    ):
        raise QuizItemForbiddenError(deck_id, reason="premium_deck")

    stmt = (
        select(Lesson)
        .join(Deck, Deck.id == Lesson.deck_id)
        .where(Lesson.deck_id == deck_id)
        .where(Lesson.archived_at.is_(None))
        .where(Lesson.published_at.is_not(None))
        .where(Deck.archived_at.is_(None))
        .where(Deck.persona_visibility.in_(visible_personas))
        .order_by(Lesson.display_order.asc(), Lesson.created_at.asc())
    )
    result = await db.execute(stmt)
    return [LessonResponse.model_validate(l) for l in result.scalars().all()]


async def get_deck_lessons_bundle(
    deck_id: str,
    db: AsyncSession,
    *,
    user: Optional[User] = None,
) -> DeckLessonsResponse | None:
    """Bundle a deck with its ordered active lessons.

    Returns ``None`` when the deck is missing, archived, or persona-
    narrowed away. Empty ``lessons`` list when the deck exists but has
    no published lessons (200, not 404). Raises
    ``QuizItemForbiddenError`` (route → 403) when the deck is premium-
    tier and the user is on the free plan (D-2 / D-10).
    """
    deck = await get_deck_with_meta(deck_id, db, user=user)
    if deck is None:
        return None
    return DeckLessonsResponse(
        deck=deck,
        lessons=await list_lessons_in_deck(deck_id, db, user=user),
    )
