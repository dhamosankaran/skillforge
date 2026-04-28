"""Read-time invariant tests for `lesson_service` (slice 6.5).

Spec: docs/specs/phase-6/06-read-time-invariants.md §10.2 + §11 AC-1..
AC-14 + §12 D-2 / D-3 / D-7 / D-10.

Locks the slice 6.5 §4.3 read-path × invariant-axis matrix for the four
lesson_service reads (R-4..R-7):

  - R-4 ``get_lesson_with_quizzes``
  - R-5 ``get_deck_with_meta``
  - R-6 ``list_lessons_in_deck``
  - R-7 ``get_deck_lessons_bundle``

Persona-mismatch (A-6) and archived-deck (A-1) violations return
``None`` / ``[]`` (route → 404). Tier mismatch (A-7) raises
``QuizItemForbiddenError`` with ``reason='premium_deck'`` (route → 403)
per D-2 / D-10. R-6 also covers the §4.3 note ³ defense-in-depth gap
(``Deck.archived_at IS NULL`` filter) so a future direct caller cannot
leak archived-deck lessons.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.subscription import Subscription
from app.models.user import User
from app.services import lesson_service
from app.services.quiz_item_study_service import QuizItemForbiddenError

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ─────────────────────────────────────────────────────────────


async def _seed_user(
    db_session,
    *,
    persona: str | None = "climber",
    plan: str = "free",
) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@lesson-invariants-test.com",
        name="Lesson Invariants Tester",
        persona=persona,
    )
    db_session.add(user)
    await db_session.flush()
    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        plan=plan,
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()
    await db_session.refresh(user, attribute_names=["subscription"])
    return user


async def _seed_deck(
    db_session,
    *,
    persona_visibility: str = "both",
    tier: str = "foundation",
    archived: bool = False,
) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"deck-{uuid.uuid4().hex[:8]}",
        title="Lesson Svc Deck",
        description="seeded",
        display_order=0,
        persona_visibility=persona_visibility,
        tier=tier,
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_lesson(
    db_session,
    deck_id: str,
    *,
    published: bool = True,
    archived: bool = False,
) -> Lesson:
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Lesson Svc Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=datetime.now(timezone.utc) if published else None,
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _seed_quiz_item(db_session, lesson_id: str) -> QuizItem:
    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        question="Q?",
        answer="A.",
        question_type="free_text",
        difficulty="medium",
        display_order=0,
        version=1,
    )
    db_session.add(qi)
    await db_session.flush()
    return qi


# ── R-4 `get_lesson_with_quizzes` ────────────────────────────────────────────


async def test_get_lesson_with_quizzes_persona_narrowed_returns_none(db_session):
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, persona_visibility="interview_prepper")
    lesson = await _seed_lesson(db_session, deck.id)
    await _seed_quiz_item(db_session, lesson.id)

    bundle = await lesson_service.get_lesson_with_quizzes(
        lesson.id, db_session, user=user
    )
    assert bundle is None


async def test_get_lesson_with_quizzes_persona_null_user_sees_only_both(db_session):
    user = await _seed_user(db_session, persona=None)
    both_deck = await _seed_deck(db_session, persona_visibility="both")
    climber_deck = await _seed_deck(db_session, persona_visibility="climber")
    both_lesson = await _seed_lesson(db_session, both_deck.id)
    climber_lesson = await _seed_lesson(db_session, climber_deck.id)
    await _seed_quiz_item(db_session, both_lesson.id)
    await _seed_quiz_item(db_session, climber_lesson.id)

    visible = await lesson_service.get_lesson_with_quizzes(
        both_lesson.id, db_session, user=user
    )
    hidden = await lesson_service.get_lesson_with_quizzes(
        climber_lesson.id, db_session, user=user
    )
    assert visible is not None
    assert visible.lesson.id == both_lesson.id
    assert hidden is None


async def test_get_lesson_with_quizzes_archived_deck_still_returns_none(db_session):
    """Slice 6.4b-1 regression: archived deck still surfaces None (route → 404)."""
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, archived=True)
    lesson = await _seed_lesson(db_session, deck.id)
    await _seed_quiz_item(db_session, lesson.id)

    bundle = await lesson_service.get_lesson_with_quizzes(
        lesson.id, db_session, user=user
    )
    assert bundle is None


async def test_get_lesson_with_quizzes_unpublished_returns_none(db_session):
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id, published=False)

    bundle = await lesson_service.get_lesson_with_quizzes(
        lesson.id, db_session, user=user
    )
    assert bundle is None


async def test_get_lesson_with_quizzes_premium_deck_free_user_raises_403(db_session):
    user = await _seed_user(db_session, persona="climber", plan="free")
    deck = await _seed_deck(db_session, tier="premium")
    lesson = await _seed_lesson(db_session, deck.id)
    await _seed_quiz_item(db_session, lesson.id)

    with pytest.raises(QuizItemForbiddenError) as excinfo:
        await lesson_service.get_lesson_with_quizzes(
            lesson.id, db_session, user=user
        )
    assert excinfo.value.reason == "premium_deck"


# ── R-5 `get_deck_with_meta` ─────────────────────────────────────────────────


async def test_get_deck_with_meta_persona_narrowed_returns_none(db_session):
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, persona_visibility="interview_prepper")

    response = await lesson_service.get_deck_with_meta(
        deck.id, db_session, user=user
    )
    assert response is None


async def test_get_deck_with_meta_premium_deck_free_user_raises_403(db_session):
    user = await _seed_user(db_session, persona="climber", plan="free")
    deck = await _seed_deck(db_session, tier="premium")

    with pytest.raises(QuizItemForbiddenError) as excinfo:
        await lesson_service.get_deck_with_meta(deck.id, db_session, user=user)
    assert excinfo.value.reason == "premium_deck"


# ── R-6 `list_lessons_in_deck` ───────────────────────────────────────────────


async def test_list_lessons_in_deck_archived_deck_returns_empty_list(db_session):
    """§4.3 note ³ defense-in-depth: even with active published lessons,
    an archived deck yields []. Anchors the slice-6.6 ranker safety net.
    """
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, archived=True)
    await _seed_lesson(db_session, deck.id)
    await _seed_lesson(db_session, deck.id)

    lessons = await lesson_service.list_lessons_in_deck(
        deck.id, db_session, user=user
    )
    assert lessons == []


async def test_list_lessons_in_deck_persona_narrowed_returns_empty_list(db_session):
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, persona_visibility="interview_prepper")
    await _seed_lesson(db_session, deck.id)

    lessons = await lesson_service.list_lessons_in_deck(
        deck.id, db_session, user=user
    )
    assert lessons == []


async def test_list_lessons_in_deck_premium_deck_free_user_raises_403(db_session):
    user = await _seed_user(db_session, persona="climber", plan="free")
    deck = await _seed_deck(db_session, tier="premium")
    await _seed_lesson(db_session, deck.id)

    with pytest.raises(QuizItemForbiddenError) as excinfo:
        await lesson_service.list_lessons_in_deck(
            deck.id, db_session, user=user
        )
    assert excinfo.value.reason == "premium_deck"


async def test_list_lessons_in_deck_visible_deck_returns_lessons(db_session):
    """Positive sanity check — the additive filters do not regress the
    happy path established by slice 6.4b-1.
    """
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)

    lessons = await lesson_service.list_lessons_in_deck(
        deck.id, db_session, user=user
    )
    assert [l.id for l in lessons] == [lesson.id]


# ── R-7 `get_deck_lessons_bundle` ────────────────────────────────────────────


async def test_get_deck_lessons_bundle_persona_narrowed_returns_none(db_session):
    """Composes via R-5 — persona-narrowed deck → None (404)."""
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, persona_visibility="interview_prepper")
    await _seed_lesson(db_session, deck.id)

    bundle = await lesson_service.get_deck_lessons_bundle(
        deck.id, db_session, user=user
    )
    assert bundle is None


async def test_get_deck_lessons_bundle_archived_deck_returns_none(db_session):
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, archived=True)
    await _seed_lesson(db_session, deck.id)

    bundle = await lesson_service.get_deck_lessons_bundle(
        deck.id, db_session, user=user
    )
    assert bundle is None


async def test_get_deck_lessons_bundle_premium_deck_free_user_raises_403(db_session):
    user = await _seed_user(db_session, persona="climber", plan="free")
    deck = await _seed_deck(db_session, tier="premium")
    await _seed_lesson(db_session, deck.id)

    with pytest.raises(QuizItemForbiddenError) as excinfo:
        await lesson_service.get_deck_lessons_bundle(
            deck.id, db_session, user=user
        )
    assert excinfo.value.reason == "premium_deck"
