"""Read-time invariant tests for `quiz_item_study_service` (slice 6.5).

Spec: docs/specs/phase-6/06-read-time-invariants.md §10.1 + §11 AC-1..
AC-14 + §12 D-2 / D-3 / D-7 / D-9.

Locks the slice 6.5 §4.3 read-path × invariant-axis matrix for the three
quiz_item_study_service reads (R-1 daily queue, R-2 review, R-3
progress aggregation):

  - persona-visibility filter (A-6) on R-1 (both queue passes) and R-2
    (post-load → ``QuizItemNotVisibleError``).
  - tier filter (A-7) on R-1 (queue inclusion) and R-2 (post-load →
    ``QuizItemForbiddenError`` with ``reason='premium_deck'``).
  - regression on slice 6.2 §AC-5 archived-deck 403 contract.
  - regression on slice 6.2 §AC-4 retired-with-progress permitted.
  - D-9 anti-regression: ``get_quiz_progress`` is filter-free for
    retention metrics.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.quiz_item_progress import QuizItemProgress
from app.models.subscription import Subscription
from app.models.user import User
from app.services import quiz_item_study_service as svc

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
        email=f"{uuid.uuid4()}@invariants-test.com",
        name="Invariants Tester",
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
        title="Invariants Deck",
        description="seeded",
        display_order=0,
        persona_visibility=persona_visibility,
        tier=tier,
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_lesson(db_session, deck_id: str) -> Lesson:
    now = datetime.now(timezone.utc)
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Invariants Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=now,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _seed_quiz_item(
    db_session, lesson_id: str, *, retired: bool = False
) -> QuizItem:
    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        question="Q?",
        answer="A.",
        question_type="free_text",
        difficulty="medium",
        display_order=0,
        version=1,
        retired_at=datetime.now(timezone.utc) if retired else None,
    )
    db_session.add(qi)
    await db_session.flush()
    return qi


async def _seed_progress(
    db_session,
    user_id: str,
    quiz_item_id: str,
    *,
    state: str = "review",
    due_delta_hours: float = -1.0,
) -> QuizItemProgress:
    now = datetime.now(timezone.utc)
    qip = QuizItemProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        quiz_item_id=quiz_item_id,
        state=state,
        stability=5.0,
        difficulty_fsrs=5.0,
        elapsed_days=0.0,
        scheduled_days=5.0,
        reps=2,
        lapses=0,
        due_date=now + timedelta(hours=due_delta_hours),
        last_reviewed=now - timedelta(days=5),
    )
    db_session.add(qip)
    await db_session.flush()
    return qip


# ── R-1 `get_daily_quiz_items` ───────────────────────────────────────────────


async def test_get_daily_quiz_items_excludes_persona_narrowed_decks(db_session):
    """A climber must not see fresh-fill quiz_items from interview_prepper-only decks."""
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, persona_visibility="interview_prepper")
    lesson = await _seed_lesson(db_session, deck.id)
    await _seed_quiz_item(db_session, lesson.id)

    response = await svc.get_daily_quiz_items(
        user_id=user.id, db=db_session, user=user
    )
    assert response.total_due == 0
    assert response.quiz_items == []


async def test_get_daily_quiz_items_includes_both_visibility_decks(db_session):
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, persona_visibility="both")
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)

    response = await svc.get_daily_quiz_items(
        user_id=user.id, db=db_session, user=user
    )
    assert response.total_due == 1
    assert response.quiz_items[0].quiz_item_id == qi.id


async def test_get_daily_quiz_items_persona_null_user_sees_only_both(db_session):
    """Persona-null users must see ``'both'``-visibility decks only (slice 6.4 D-19 read-side)."""
    user = await _seed_user(db_session, persona=None)
    both_deck = await _seed_deck(db_session, persona_visibility="both")
    climber_deck = await _seed_deck(db_session, persona_visibility="climber")
    both_lesson = await _seed_lesson(db_session, both_deck.id)
    climber_lesson = await _seed_lesson(db_session, climber_deck.id)
    both_qi = await _seed_quiz_item(db_session, both_lesson.id)
    await _seed_quiz_item(db_session, climber_lesson.id)

    response = await svc.get_daily_quiz_items(
        user_id=user.id, db=db_session, user=user
    )
    assert {qi.quiz_item_id for qi in response.quiz_items} == {both_qi.id}


async def test_get_daily_quiz_items_excludes_premium_decks_for_free_user(db_session):
    """Free user, premium deck — quiz_items never surface in the queue (D-2)."""
    user = await _seed_user(db_session, persona="climber", plan="free")
    deck = await _seed_deck(db_session, tier="premium")
    lesson = await _seed_lesson(db_session, deck.id)
    await _seed_quiz_item(db_session, lesson.id)

    response = await svc.get_daily_quiz_items(
        user_id=user.id, db=db_session, user=user
    )
    assert response.total_due == 0


async def test_get_daily_quiz_items_includes_premium_decks_for_pro_user(db_session):
    """Pro user, premium deck — quiz_items surface (D-2 negative case)."""
    user = await _seed_user(db_session, persona="climber", plan="pro")
    deck = await _seed_deck(db_session, tier="premium")
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)

    response = await svc.get_daily_quiz_items(
        user_id=user.id, db=db_session, user=user
    )
    assert response.total_due == 1
    assert response.quiz_items[0].quiz_item_id == qi.id


# ── R-2 `review_quiz_item` ───────────────────────────────────────────────────


async def test_review_quiz_item_persona_mismatch_raises_404(db_session):
    """Persona mismatch on review path → ``QuizItemNotVisibleError`` (D-7 → 404)."""
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, persona_visibility="interview_prepper")
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)

    with pytest.raises(svc.QuizItemNotVisibleError):
        await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )


async def test_review_quiz_item_persona_match_succeeds(db_session):
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, persona_visibility="climber")
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)

    response = await svc.review_quiz_item(
        user_id=user.id,
        quiz_item_id=qi.id,
        rating=3,
        db=db_session,
        user=user,
    )
    assert response.quiz_item_id == qi.id


async def test_review_quiz_item_archived_deck_still_403(db_session):
    """Slice 6.2 §AC-5 regression: archived deck still raises ``QuizItemForbiddenError`` (403)."""
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session, archived=True)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)

    with pytest.raises(svc.QuizItemForbiddenError) as excinfo:
        await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )
    assert excinfo.value.reason == "archived"


async def test_review_quiz_item_retired_with_progress_still_succeeds(db_session):
    """Slice 6.2 §AC-4 regression: retired-with-existing-progress still permitted."""
    user = await _seed_user(db_session, persona="climber")
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id, retired=True)
    await _seed_progress(db_session, user.id, qi.id)

    response = await svc.review_quiz_item(
        user_id=user.id,
        quiz_item_id=qi.id,
        rating=3,
        db=db_session,
        user=user,
    )
    assert response.quiz_item_id == qi.id


async def test_review_quiz_item_premium_deck_free_user_403(db_session):
    """D-2: premium deck + free user → ``QuizItemForbiddenError`` (reason='premium_deck')."""
    user = await _seed_user(db_session, persona="climber", plan="free")
    deck = await _seed_deck(db_session, tier="premium")
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)

    with pytest.raises(svc.QuizItemForbiddenError) as excinfo:
        await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )
    assert excinfo.value.reason == "premium_deck"


# ── R-3 `get_quiz_progress` (D-9 anti-regression) ────────────────────────────


async def test_get_quiz_progress_counts_progress_on_archived_lessons(db_session):
    """D-9 positive invariant: archived/retired/persona-narrowed orphan rows
    stay counted in ``total_reps`` / ``total_lapses`` / ``by_state``. Future
    slice 6.16 retention dashboard MUST NOT silently filter this aggregate.
    """
    user = await _seed_user(db_session, persona="climber")
    # Three orphaned-but-historical scenarios. All progress rows must count.
    archived_deck = await _seed_deck(db_session, archived=True)
    archived_deck_lesson = await _seed_lesson(db_session, archived_deck.id)
    qi_archived_deck = await _seed_quiz_item(db_session, archived_deck_lesson.id)

    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi_retired = await _seed_quiz_item(db_session, lesson.id, retired=True)

    narrowed_deck = await _seed_deck(db_session, persona_visibility="interview_prepper")
    narrowed_lesson = await _seed_lesson(db_session, narrowed_deck.id)
    qi_narrowed = await _seed_quiz_item(db_session, narrowed_lesson.id)

    for qi in (qi_archived_deck, qi_retired, qi_narrowed):
        await _seed_progress(db_session, user.id, qi.id, state="review")

    response = await svc.get_quiz_progress(user_id=user.id, db=db_session)
    assert response.by_state["review"] == 3
    assert response.total_reviewed == 3
    # Each seeded progress row has reps=2 (per `_seed_progress`).
    assert response.total_reps == 6
