"""Dual-write integration tests for `quiz_item_study_service.review_quiz_item`.

Spec: docs/specs/phase-6/00-analytics-tables.md §6.2 + §10.2 + AC-3 + AC-5.

Verifies the slice-6.0 dual-write hook at the existing `quiz_item_reviewed`
PostHog emission site (`quiz_item_study_service.py:438-451`):

  1. PostHog `analytics_track('quiz_item_reviewed', ...)` still fires.
  2. Postgres `quiz_review_events` row is written with denormalized
     `lesson_id` + `deck_id` (D-8) and the same FSRS state values as the
     PostHog payload.
  3. D-7 best-effort failure: a Postgres write failure does not block the
     user's review request (the existing PostHog event still fires and the
     service returns the QuizReviewResponse).
  4. D-7 best-effort failure: a PostHog failure does not block the Postgres
     write or the user's review request.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.user import User
from app.services import (
    analytics_event_service,
    quiz_item_study_service as svc,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ─────────────────────────────────────────────────────────────


async def _seed_user(db_session) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@dual-write-test.com",
        name="Dual-Write Tester",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_chain(db_session):
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"deck-{uuid.uuid4().hex[:6]}",
        title="Dual Test",
        description="dual",
        display_order=0,
        persona_visibility="both",
        tier="foundation",
    )
    db_session.add(deck)
    await db_session.flush()

    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck.id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Dual Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
    )
    db_session.add(lesson)
    await db_session.flush()

    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson.id,
        question="Q?",
        answer="A.",
        question_type="free_text",
        difficulty="medium",
        display_order=0,
        version=1,
    )
    db_session.add(qi)
    await db_session.flush()
    return deck, lesson, qi


# ── AC-3: both legs of dual-write fire ───────────────────────────────────────


async def test_review_quiz_item_writes_quiz_review_events_row(db_session):
    user = await _seed_user(db_session)
    _, _, qi = await _seed_chain(db_session)

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

    assert resp.quiz_item_id == qi.id

    # PostHog leg.
    events = [name for name, _ in fired]
    assert events.count("quiz_item_reviewed") == 1, fired

    # Postgres leg.
    rows = (
        await db_session.execute(
            text("SELECT quiz_item_id, rating, reps, lapses FROM quiz_review_events "
                 "WHERE quiz_item_id = :qid"),
            {"qid": qi.id},
        )
    ).all()
    assert len(rows) == 1, "exactly one quiz_review_events row per review"
    assert rows[0].rating == 3
    assert rows[0].reps == 1
    assert rows[0].lapses == 0


async def test_review_quiz_item_denormalizes_lesson_and_deck_id(db_session):
    """D-8 — denormalized lesson_id + deck_id match the source FK chain."""
    user = await _seed_user(db_session)
    deck, lesson, qi = await _seed_chain(db_session)

    with patch.object(svc, "analytics_track"):
        await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )

    rows = (
        await db_session.execute(
            text("SELECT lesson_id, deck_id FROM quiz_review_events "
                 "WHERE quiz_item_id = :qid"),
            {"qid": qi.id},
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].lesson_id == lesson.id
    assert rows[0].deck_id == deck.id


async def test_review_quiz_item_writes_correct_state_transitions(db_session):
    """First review: fsrs_state_before='new'; matches PostHog payload."""
    user = await _seed_user(db_session)
    _, _, qi = await _seed_chain(db_session)

    fired: list[dict] = []

    def _capture(*, user_id, event, properties=None):
        if event == "quiz_item_reviewed":
            fired.append(properties or {})

    with patch.object(svc, "analytics_track", side_effect=_capture):
        await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )

    assert len(fired) == 1
    posthog_props = fired[0]
    assert posthog_props["fsrs_state_before"] == "new"

    rows = (
        await db_session.execute(
            text("SELECT fsrs_state_before, fsrs_state_after FROM quiz_review_events "
                 "WHERE quiz_item_id = :qid"),
            {"qid": qi.id},
        )
    ).all()
    assert len(rows) == 1
    # Payload-parity per spec §6.2: PostHog and Postgres carry the same FSRS
    # state vocab on first review.
    assert rows[0].fsrs_state_before == posthog_props["fsrs_state_before"]
    assert rows[0].fsrs_state_after == posthog_props["fsrs_state_after"]


# ── AC-5: D-7 best-effort failure semantics ─────────────────────────────────


async def test_review_quiz_item_postgres_failure_does_not_block_request(db_session):
    """D-7 — write_quiz_review_event SQLAlchemyError is swallowed; review
    request still returns + PostHog still fires."""
    user = await _seed_user(db_session)
    _, _, qi = await _seed_chain(db_session)

    fired: list[str] = []

    def _capture(*, user_id, event, properties=None):
        fired.append(event)

    async def _boom_write(*args, **kwargs):
        raise SQLAlchemyError("simulated write failure")

    with patch.object(svc, "analytics_track", side_effect=_capture), \
         patch.object(
             analytics_event_service,
             "write_quiz_review_event",
             side_effect=_boom_write,
         ):
        resp = await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )

    # User request still resolved.
    assert resp.quiz_item_id == qi.id
    # PostHog still fired (analytical critical-path is preserved).
    assert "quiz_item_reviewed" in fired


async def test_review_quiz_item_posthog_failure_does_not_block_postgres_write(db_session):
    """D-7 — analytics_track failure does not abort the Postgres write or
    the user request. The user-blocking critical path is the FSRS update,
    not analytics."""
    user = await _seed_user(db_session)
    _, _, qi = await _seed_chain(db_session)

    def _boom_track(*, user_id, event, properties=None):
        raise RuntimeError("simulated PostHog outage")

    with patch.object(svc, "analytics_track", side_effect=_boom_track):
        resp = await svc.review_quiz_item(
            user_id=user.id,
            quiz_item_id=qi.id,
            rating=3,
            db=db_session,
            user=user,
        )

    assert resp.quiz_item_id == qi.id
    rows = (
        await db_session.execute(
            text("SELECT 1 FROM quiz_review_events WHERE quiz_item_id = :qid"),
            {"qid": qi.id},
        )
    ).all()
    assert len(rows) == 1, "Postgres dual-write fires even when PostHog fails"
