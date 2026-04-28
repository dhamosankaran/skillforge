"""Unit tests for `app/services/analytics_event_service.py` (spec 6.0 §10.3).

Covers:
  - Happy-path inserts for both `write_quiz_review_event` +
    `write_lesson_view_event`.
  - D-7 best-effort failure semantics: SQLAlchemyError → log + return None.
  - Anonymized writes (user_id=None) for post-account-deletion replay.
  - Null plan / persona for the service-test path where subscription is
    not eagerly loaded.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.user import User
from app.schemas.analytics_event import (
    LessonViewEventCreate,
    QuizReviewEventCreate,
)
from app.services import analytics_event_service as svc

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ─────────────────────────────────────────────────────────────


async def _seed_chain(db_session):
    """Create deck → lesson → quiz_item chain. Returns IDs only."""
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"deck-{uuid.uuid4().hex[:6]}",
        title="Analytics Test Deck",
        description="Test",
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
        title="Test Lesson",
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

    return deck.id, lesson.id, qi.id


async def _seed_user_id(db_session) -> str:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@analytics-svc-test.com",
        name="Analytics Tester",
    )
    db_session.add(user)
    await db_session.flush()
    return user.id


# ── Happy paths ──────────────────────────────────────────────────────────────


async def test_write_quiz_review_event_inserts_row(db_session):
    deck_id, lesson_id, qi_id = await _seed_chain(db_session)
    user_id = await _seed_user_id(db_session)

    payload = QuizReviewEventCreate(
        user_id=user_id,
        quiz_item_id=qi_id,
        lesson_id=lesson_id,
        deck_id=deck_id,
        rating=3,
        fsrs_state_before="new",
        fsrs_state_after="learning",
        reps=1,
        lapses=0,
        time_spent_ms=1200,
        session_id="sess-abc",
        plan="free",
        persona="career_climber",
    )
    result = await svc.write_quiz_review_event(payload, db_session)
    assert result is None  # Write-only, no return value.

    rows = (
        await db_session.execute(
            text("SELECT user_id, quiz_item_id, lesson_id, deck_id, rating, "
                 "fsrs_state_before, fsrs_state_after, reps, lapses, "
                 "time_spent_ms, session_id, plan, persona "
                 "FROM quiz_review_events WHERE quiz_item_id = :qid"),
            {"qid": qi_id},
        )
    ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == user_id
    assert row.quiz_item_id == qi_id
    assert row.lesson_id == lesson_id
    assert row.deck_id == deck_id
    assert row.rating == 3
    assert row.fsrs_state_before == "new"
    assert row.fsrs_state_after == "learning"
    assert row.reps == 1
    assert row.lapses == 0
    assert row.time_spent_ms == 1200
    assert row.session_id == "sess-abc"
    assert row.plan == "free"
    assert row.persona == "career_climber"


async def test_write_lesson_view_event_inserts_row(db_session):
    deck_id, lesson_id, _ = await _seed_chain(db_session)
    user_id = await _seed_user_id(db_session)

    payload = LessonViewEventCreate(
        user_id=user_id,
        lesson_id=lesson_id,
        deck_id=deck_id,
        version=1,
        session_id="sess-xyz",
        plan="pro",
        persona="interview_prepper",
    )
    result = await svc.write_lesson_view_event(payload, db_session)
    assert result is None

    rows = (
        await db_session.execute(
            text("SELECT user_id, lesson_id, deck_id, version, session_id, plan, persona "
                 "FROM lesson_view_events WHERE lesson_id = :lid"),
            {"lid": lesson_id},
        )
    ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == user_id
    assert row.lesson_id == lesson_id
    assert row.deck_id == deck_id
    assert row.version == 1
    assert row.session_id == "sess-xyz"
    assert row.plan == "pro"
    assert row.persona == "interview_prepper"


# ── Anonymized + null branches ──────────────────────────────────────────────


async def test_write_quiz_review_event_handles_null_user_id(db_session):
    """Anonymized write — post-account-deletion replay scenario (D-1)."""
    deck_id, lesson_id, qi_id = await _seed_chain(db_session)

    payload = QuizReviewEventCreate(
        user_id=None,
        quiz_item_id=qi_id,
        lesson_id=lesson_id,
        deck_id=deck_id,
        rating=4,
        fsrs_state_before="review",
        fsrs_state_after="review",
        reps=5,
        lapses=1,
    )
    await svc.write_quiz_review_event(payload, db_session)
    rows = (
        await db_session.execute(
            text("SELECT user_id FROM quiz_review_events WHERE quiz_item_id = :qid"),
            {"qid": qi_id},
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].user_id is None


async def test_write_quiz_review_event_handles_null_plan_persona(db_session):
    """Null plan/persona (subscription not eagerly loaded)."""
    deck_id, lesson_id, qi_id = await _seed_chain(db_session)
    user_id = await _seed_user_id(db_session)

    payload = QuizReviewEventCreate(
        user_id=user_id,
        quiz_item_id=qi_id,
        lesson_id=lesson_id,
        deck_id=deck_id,
        rating=2,
        fsrs_state_before="learning",
        fsrs_state_after="learning",
        reps=1,
        lapses=1,
        plan=None,
        persona=None,
    )
    await svc.write_quiz_review_event(payload, db_session)
    rows = (
        await db_session.execute(
            text("SELECT plan, persona FROM quiz_review_events WHERE quiz_item_id = :qid"),
            {"qid": qi_id},
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].plan is None
    assert rows[0].persona is None


# ── D-7 failure semantics ────────────────────────────────────────────────────


async def test_write_quiz_review_event_returns_none_on_sqlalchemy_error(db_session, caplog):
    """SQLAlchemyError during insert is logged, function returns None (D-7)."""
    deck_id, lesson_id, qi_id = await _seed_chain(db_session)

    payload = QuizReviewEventCreate(
        user_id=None,
        quiz_item_id=qi_id,
        lesson_id=lesson_id,
        deck_id=deck_id,
        rating=3,
        fsrs_state_before="new",
        fsrs_state_after="learning",
        reps=1,
        lapses=0,
    )

    async def _boom(*args, **kwargs):
        raise SQLAlchemyError("simulated insert failure")

    with patch.object(db_session, "flush", new=_boom):
        with caplog.at_level("ERROR"):
            result = await svc.write_quiz_review_event(payload, db_session)
    assert result is None
    # logger.exception fires under failure path.
    assert any("analytics_event_write_failed" in rec.message for rec in caplog.records)


async def test_write_lesson_view_event_returns_none_on_sqlalchemy_error(db_session, caplog):
    """Same D-7 contract for the lesson_view_events writer."""
    deck_id, lesson_id, _ = await _seed_chain(db_session)

    payload = LessonViewEventCreate(
        user_id=None,
        lesson_id=lesson_id,
        deck_id=deck_id,
        version=1,
    )

    async def _boom(*args, **kwargs):
        raise SQLAlchemyError("simulated insert failure")

    with patch.object(db_session, "flush", new=_boom):
        with caplog.at_level("ERROR"):
            result = await svc.write_lesson_view_event(payload, db_session)
    assert result is None
    assert any("analytics_event_write_failed" in rec.message for rec in caplog.records)
