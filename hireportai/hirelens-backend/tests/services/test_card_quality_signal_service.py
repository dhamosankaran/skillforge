"""Service tests for ``card_quality_signal_service`` (Phase 6 slice 6.13.5a).

Spec: docs/specs/phase-6/12-quality-signals.md §6.1 + §11 AC-3 / AC-4 +
§12 D-5 / D-8.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.card_quality_signal import CardQualitySignal
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.user import User
from app.schemas.card_quality_signal import CardQualitySignalWrite
from app.services import card_quality_signal_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_deck(db_session) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"sig-deck-{uuid.uuid4().hex[:8]}",
        title="Signal Test Deck",
        description="seed",
        display_order=0,
        persona_visibility="both",
        tier="foundation",
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_lesson(db_session, deck_id: str) -> Lesson:
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Signal Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=datetime.now(timezone.utc),
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


async def _seed_user(db_session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        email=f"u-{uuid.uuid4().hex[:8]}@example.com",
        name="Signal User",
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ── 1. UPSERT happy path (AC-3) ────────────────────────────────────────────


async def test_upsert_signal_inserts_new_row(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)

    row = await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=None,
            signal_source="critique",
            dimension="accuracy",
            score=0.8,
            source_ref="job-1",
            recorded_by_user_id=None,
        ),
        db_session,
    )

    assert row.id is not None
    assert row.lesson_id == lesson.id
    assert row.signal_source == "critique"
    assert row.dimension == "accuracy"
    assert float(row.score) == 0.8
    assert row.source_ref == "job-1"


# ── 2. UPSERT idempotency (AC-3) ────────────────────────────────────────────


async def test_upsert_signal_overwrites_on_conflict(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)

    first = await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=None,
            signal_source="critique",
            dimension="accuracy",
            score=0.8,
            source_ref="job-1",
        ),
        db_session,
    )
    second = await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=None,
            signal_source="critique",
            dimension="accuracy",
            score=0.6,  # changed
            source_ref="job-2",  # changed
        ),
        db_session,
    )

    # Same row identity (UPSERT, not INSERT-twice).
    assert first.id == second.id
    # Score + source_ref overwrote per ON CONFLICT DO UPDATE.
    refreshed = (
        await db_session.execute(
            select(CardQualitySignal).where(CardQualitySignal.id == first.id)
        )
    ).scalar_one()
    assert float(refreshed.score) == 0.6
    assert refreshed.source_ref == "job-2"

    # And only one row exists.
    all_rows = (await db_session.execute(select(CardQualitySignal))).scalars().all()
    assert len(all_rows) == 1


# ── 3. NULL-distinct UNIQUE constraint (AC-4) ──────────────────────────────


async def test_unique_constraint_treats_null_quiz_item_as_distinct(db_session):
    """Lesson-level row + quiz_item-level row co-exist (AC-4)."""
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)

    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=None,
            signal_source="user_review",
            dimension="pass_rate",
            score=0.7,
        ),
        db_session,
    )
    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=qi.id,
            signal_source="user_review",
            dimension="pass_rate",
            score=0.5,
        ),
        db_session,
    )

    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.lesson_id == lesson.id
            )
        )
    ).scalars().all()
    assert len(rows) == 2


# ── 4. NULL-distinct UNIQUE on recorded_by_user_id (D-5 5-tuple) ───────────


async def test_unique_includes_recorded_by_user_id_for_thumbs(db_session):
    """Two users can each leave their own thumbs row on the same lesson."""
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    user_a = await _seed_user(db_session)
    user_b = await _seed_user(db_session)

    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=None,
            signal_source="user_thumbs",
            dimension="helpful",
            score=1.0,
            recorded_by_user_id=user_a.id,
        ),
        db_session,
    )
    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=None,
            signal_source="user_thumbs",
            dimension="helpful",
            score=-1.0,
            recorded_by_user_id=user_b.id,
        ),
        db_session,
    )

    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.lesson_id == lesson.id,
                CardQualitySignal.signal_source == "user_thumbs",
            )
        )
    ).scalars().all()
    assert len(rows) == 2
    assert {r.recorded_by_user_id for r in rows} == {user_a.id, user_b.id}


# ── 5. Critique-score reader returns nested dict (§6.1 reader API) ─────────


async def test_get_critique_scores_for_lessons_groups_by_lesson(db_session):
    deck = await _seed_deck(db_session)
    lesson_a = await _seed_lesson(db_session, deck.id)
    lesson_b = await _seed_lesson(db_session, deck.id)
    for dim in ("accuracy", "clarity"):
        await card_quality_signal_service.upsert_signal(
            CardQualitySignalWrite(
                lesson_id=lesson_a.id,
                signal_source="critique",
                dimension=dim,
                score=0.8,
            ),
            db_session,
        )
    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson_b.id,
            signal_source="critique",
            dimension="cohesion",
            score=0.6,
        ),
        db_session,
    )

    out = await card_quality_signal_service.get_critique_scores_for_lessons(
        [lesson_a.id, lesson_b.id], db_session
    )

    assert set(out.keys()) == {lesson_a.id, lesson_b.id}
    assert out[lesson_a.id] == {"accuracy": 0.8, "clarity": 0.8}
    assert out[lesson_b.id] == {"cohesion": 0.6}


async def test_get_critique_scores_for_lessons_returns_empty_when_cold(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)

    out = await card_quality_signal_service.get_critique_scores_for_lessons(
        [lesson.id], db_session
    )
    assert out == {}


# ── 6. Critique reader filters out per-quiz_item rows ──────────────────────


async def test_get_critique_scores_skips_per_quiz_item_critique(db_session):
    """Per-quiz_item critique rows aren't part of v1 (§12 D-3 + §4.2.1)."""
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)
    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=qi.id,  # NON-NULL — should be filtered out by the reader
            signal_source="critique",
            dimension="accuracy",
            score=0.5,
        ),
        db_session,
    )

    out = await card_quality_signal_service.get_critique_scores_for_lessons(
        [lesson.id], db_session
    )
    assert out == {}


# ── 7. Persisted user_review reader returns per-quiz_item map ──────────────


async def test_get_persisted_user_review_scores_returns_per_quiz_item(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    qi = await _seed_quiz_item(db_session, lesson.id)
    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            quiz_item_id=qi.id,
            signal_source="user_review",
            dimension="pass_rate",
            score=0.65,
        ),
        db_session,
    )

    out = await card_quality_signal_service.get_persisted_user_review_scores_for_quiz_items(
        [qi.id], db_session
    )
    assert out == {qi.id: 0.65}


# ── 8. get_signals_for_lesson source filter ────────────────────────────────


async def test_get_signals_for_lesson_filters_by_source(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            signal_source="critique",
            dimension="accuracy",
            score=0.8,
        ),
        db_session,
    )
    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson.id,
            signal_source="user_review",
            dimension="pass_rate",
            score=0.7,
        ),
        db_session,
    )

    critique_only = await card_quality_signal_service.get_signals_for_lesson(
        lesson.id, db_session, signal_source="critique"
    )
    assert len(critique_only) == 1
    assert critique_only[0].signal_source == "critique"

    all_for_lesson = await card_quality_signal_service.get_signals_for_lesson(
        lesson.id, db_session
    )
    assert len(all_for_lesson) == 2
