"""Unit tests for `app/services/quiz_item_study_service.py` (spec 6.2 §10.1).

Covers:
  - FSRS Card reconstruction (`_build_fsrs_quiz_card`).
  - Write-back (`_apply_fsrs_result_to_quiz_item`).
  - Two-pass daily queue (overdue + fresh-fill).
  - Retired-quiz / archived-lesson / archived-deck filtering.
  - First-review creates a progress row + fires
    `quiz_item_progress_initialized`.
  - Subsequent reviews update; do NOT fire
    `quiz_item_progress_initialized`.
  - Retired-quiz guard blocks NEW reviews; allows updates to existing.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from fsrs import State

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.quiz_item_progress import QuizItemProgress
from app.models.user import User
from app.services import quiz_item_study_service as svc

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ─────────────────────────────────────────────────────────────


async def _seed_user(db_session) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@quiz-svc-test.com",
        name="Quiz Svc Tester",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_deck(db_session, *, archived: bool = False) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"deck-{uuid.uuid4().hex[:6]}",
        title="Test Deck",
        description="Tests",
        display_order=0,
        persona_visibility="both",
        tier="foundation",
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_lesson(
    db_session, deck_id: str, *, archived: bool = False
) -> Lesson:
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Test Lesson",
        concept_md="concept",
        production_md="production",
        examples_md="examples",
        display_order=0,
        version=1,
        version_type="initial",
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _seed_quiz_item(
    db_session,
    lesson_id: str,
    *,
    retired: bool = False,
    created_offset_seconds: int = 0,
) -> QuizItem:
    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        question=f"Q-{uuid.uuid4().hex[:6]}?",
        answer="A.",
        question_type="free_text",
        difficulty="medium",
        display_order=0,
        version=1,
        retired_at=datetime.now(timezone.utc) if retired else None,
    )
    if created_offset_seconds:
        qi.created_at = datetime.now(timezone.utc) + timedelta(
            seconds=created_offset_seconds
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


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _setup(db_session, *, archived_lesson=False, archived_deck=False, retired_quiz=False):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session, archived=archived_deck)
    lesson = await _seed_lesson(db_session, deck.id, archived=archived_lesson)
    qi = await _seed_quiz_item(db_session, lesson.id, retired=retired_quiz)
    return user, deck, lesson, qi


# ── _build_fsrs_quiz_card ────────────────────────────────────────────────────


async def test_build_fsrs_quiz_card_new_state(db_session):
    user, _, _, qi = await _setup(db_session)
    progress = QuizItemProgress(
        id=str(uuid.uuid4()),
        user_id=user.id,
        quiz_item_id=qi.id,
        state="new",
        stability=0.0,
        difficulty_fsrs=0.0,
    )
    fsrs_card = svc._build_fsrs_quiz_card(progress)
    # Fresh FsrsCard — py-fsrs treats this as Learning step=0 on first review.
    assert fsrs_card.state == State.Learning  # py-fsrs default state


async def test_build_fsrs_quiz_card_review_state(db_session):
    user, _, _, qi = await _setup(db_session)
    progress = await _seed_progress(db_session, user.id, qi.id, state="review")
    fsrs_card = svc._build_fsrs_quiz_card(progress)
    assert fsrs_card.state == State.Review
    assert fsrs_card.stability == 5.0
    assert fsrs_card.difficulty == 5.0
    assert fsrs_card.due == progress.due_date
    assert fsrs_card.last_review == progress.last_reviewed


# ── _apply_fsrs_result_to_quiz_item ──────────────────────────────────────────


async def test_apply_fsrs_result_writes_back(db_session):
    user, _, _, qi = await _setup(db_session)
    progress = await _seed_progress(db_session, user.id, qi.id, state="review")

    now = datetime.now(timezone.utc)

    # Mock-ish updated FsrsCard via the real py-fsrs scheduler call.
    fsrs_card = svc._build_fsrs_quiz_card(progress)
    from fsrs import Rating
    updated, _ = svc._scheduler.review_card(fsrs_card, Rating.Good, review_datetime=now)

    svc._apply_fsrs_result_to_quiz_item(progress, updated, elapsed_days=1.0, now=now)

    assert progress.state in ("learning", "review", "relearning")
    assert progress.last_reviewed == now
    assert progress.elapsed_days == 1.0
    assert progress.scheduled_days >= 0.0
    assert progress.due_date == updated.due


# ── get_daily_quiz_items — two-pass + filters ────────────────────────────────


async def test_get_daily_quiz_items_two_pass(db_session):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)

    # 3 overdue + 5 unreviewed quiz_items.
    overdue_qis = []
    for _ in range(3):
        qi = await _seed_quiz_item(db_session, lesson.id)
        await _seed_progress(db_session, user.id, qi.id, state="review", due_delta_hours=-1)
        overdue_qis.append(qi)

    unreviewed_qis = []
    for i in range(5):
        qi = await _seed_quiz_item(db_session, lesson.id, created_offset_seconds=i)
        unreviewed_qis.append(qi)

    resp = await svc.get_daily_quiz_items(user_id=user.id, db=db_session, user=user)

    # _DAILY_GOAL = 5: 3 overdue + 2 fresh-fill.
    assert resp.total_due == 5
    assert len(resp.quiz_items) == 5

    # First 3 are the overdue (have due_date set; non-new state).
    for item in resp.quiz_items[:3]:
        assert item.fsrs_state in ("learning", "review", "relearning")
        assert item.due_date is not None

    # Last 2 are fresh-fill (state="new", due_date=None, reps=lapses=0).
    for item in resp.quiz_items[3:]:
        assert item.fsrs_state == "new"
        assert item.due_date is None
        assert item.reps == 0
        assert item.lapses == 0


async def test_get_daily_quiz_items_excludes_retired(db_session):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)

    # Active quiz_item should be returned; retired one filtered out of fresh-fill.
    active_qi = await _seed_quiz_item(db_session, lesson.id)
    retired_qi = await _seed_quiz_item(db_session, lesson.id, retired=True)

    resp = await svc.get_daily_quiz_items(user_id=user.id, db=db_session, user=user)

    quiz_item_ids = {item.quiz_item_id for item in resp.quiz_items}
    assert active_qi.id in quiz_item_ids
    assert retired_qi.id not in quiz_item_ids


async def test_get_daily_quiz_items_excludes_archived(db_session):
    user = await _seed_user(db_session)

    # Archived lesson — quiz_items underneath should be filtered.
    deck1 = await _seed_deck(db_session)
    archived_lesson = await _seed_lesson(db_session, deck1.id, archived=True)
    arch_lesson_qi = await _seed_quiz_item(db_session, archived_lesson.id)

    # Archived deck — quiz_items underneath should be filtered.
    deck_archived = await _seed_deck(db_session, archived=True)
    lesson_under_arch_deck = await _seed_lesson(db_session, deck_archived.id)
    arch_deck_qi = await _seed_quiz_item(db_session, lesson_under_arch_deck.id)

    # Active sentinel.
    deck_ok = await _seed_deck(db_session)
    lesson_ok = await _seed_lesson(db_session, deck_ok.id)
    ok_qi = await _seed_quiz_item(db_session, lesson_ok.id)

    resp = await svc.get_daily_quiz_items(user_id=user.id, db=db_session, user=user)

    quiz_item_ids = {item.quiz_item_id for item in resp.quiz_items}
    assert ok_qi.id in quiz_item_ids
    assert arch_lesson_qi.id not in quiz_item_ids
    assert arch_deck_qi.id not in quiz_item_ids


# ── review_quiz_item — first review + analytics events ──────────────────────


async def test_review_quiz_item_creates_progress_row(db_session):
    user, _, lesson, qi = await _setup(db_session)

    fired: list[tuple[str, dict]] = []

    def _capture(*, user_id, event, properties=None):
        fired.append((event, properties or {}))

    with patch.object(svc, "analytics_track", side_effect=_capture):
        resp = await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,  # Good
            db=db_session,
            user=user,
        )

    assert resp.quiz_item_id == qi.id
    assert resp.fsrs_state in ("learning", "review", "relearning")
    assert resp.reps == 1
    assert resp.lapses == 0

    events = [name for name, _ in fired]
    assert "quiz_item_progress_initialized" in events
    assert "quiz_item_reviewed" in events

    init_props = next(p for name, p in fired if name == "quiz_item_progress_initialized")
    assert init_props["quiz_item_id"] == qi.id
    assert init_props["lesson_id"] == lesson.id
    assert "deck_id" in init_props


async def test_review_quiz_item_updates_existing_no_init_event(db_session):
    user, _, _, qi = await _setup(db_session)
    await _seed_progress(db_session, user.id, qi.id, state="review")

    fired: list[tuple[str, dict]] = []

    def _capture(*, user_id, event, properties=None):
        fired.append((event, properties or {}))

    with patch.object(svc, "analytics_track", side_effect=_capture):
        resp = await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )

    assert resp.reps == 3  # 2 + 1

    events = [name for name, _ in fired]
    assert "quiz_item_progress_initialized" not in events
    assert "quiz_item_reviewed" in events


# ── review_quiz_item — retired guard ─────────────────────────────────────────


async def test_review_quiz_item_retired_blocks_new(db_session):
    user, _, _, qi = await _setup(db_session, retired_quiz=True)

    with pytest.raises(svc.QuizItemRetiredError):
        await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )


async def test_review_quiz_item_retired_allows_existing(db_session):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)

    # Quiz_item starts active; user has progress; quiz_item then retires.
    qi = await _seed_quiz_item(db_session, lesson.id)
    await _seed_progress(db_session, user.id, qi.id, state="review")
    qi.retired_at = datetime.now(timezone.utc)
    await db_session.flush()

    resp = await svc.review_quiz_item(
        user_id=user.id,
        quiz_item_id=qi.id,
        rating=3,
        db=db_session,
        user=user,
    )
    assert resp.quiz_item_id == qi.id
    assert resp.reps == 3  # history preserved + bumped


# ── _compute_daily_quiz_status — sentinel only (D-4) ─────────────────────────


async def test_compute_daily_quiz_status_sentinel(db_session):
    user = await _seed_user(db_session)
    status = await svc._compute_daily_quiz_status(user, db_session)
    assert status.cards_consumed == 0
    assert status.cards_limit == -1
    assert status.can_review is True
    assert status.resets_at.tzinfo is not None


# ── get_quiz_progress — aggregate stats ──────────────────────────────────────


async def test_get_quiz_progress_aggregates(db_session):
    user = await _seed_user(db_session)
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)

    # 1 in review state, 1 in learning state.
    qi1 = await _seed_quiz_item(db_session, lesson.id)
    await _seed_progress(db_session, user.id, qi1.id, state="review")

    qi2 = await _seed_quiz_item(db_session, lesson.id)
    await _seed_progress(db_session, user.id, qi2.id, state="learning")

    progress = await svc.get_quiz_progress(user_id=user.id, db=db_session)

    assert progress.total_reviewed == 2
    assert progress.by_state["review"] == 1
    assert progress.by_state["learning"] == 1
    assert progress.total_reps == 4  # 2 per row × 2 rows
    assert progress.total_lapses == 0
