"""Tests for ``critique_signal_consumer`` (Phase 6 slice 6.13.5a).

Spec: docs/specs/phase-6/12-quality-signals.md §6.2 + §11 AC-9 / AC-10 +
§12 D-3.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.card_quality_signal import CardQualitySignal
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.schemas.ingestion import CritiqueDimension, CritiqueSchema
from app.services import critique_signal_consumer

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_deck(db_session) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"crit-deck-{uuid.uuid4().hex[:8]}",
        title="Critique Deck",
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
        title="Critique Lesson",
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


def _make_critique(scores: dict[str, int]) -> CritiqueSchema:
    return CritiqueSchema(
        verdict="PASS",
        rationale="Looks good.",
        dimensions=[
            CritiqueDimension(name=name, score=score, rationale="ok")  # type: ignore[arg-type]
            for name, score in scores.items()
        ],
    )


# ── 1. AC-9: 4 dimensions × 1 lesson = 4 rows ──────────────────────────────


async def test_persist_writes_one_row_per_dimension(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    critique = _make_critique(
        {"accuracy": 4, "clarity": 5, "completeness": 3, "cohesion": 5}
    )
    job_id = str(uuid.uuid4())

    written = await critique_signal_consumer.persist_critique_signals(
        lesson_ids=[lesson.id],
        critique=critique,
        job_id=job_id,
        db=db_session,
    )

    assert written == 4
    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.lesson_id == lesson.id,
                CardQualitySignal.signal_source == "critique",
            )
        )
    ).scalars().all()
    assert len(rows) == 4
    by_dim = {r.dimension: r for r in rows}
    # Score normalisation: dimension.score / 5.0.
    assert float(by_dim["accuracy"].score) == 0.8
    assert float(by_dim["clarity"].score) == 1.0
    assert float(by_dim["completeness"].score) == 0.6
    assert float(by_dim["cohesion"].score) == 1.0
    # Provenance: source_ref points at the ingestion job.
    assert all(r.source_ref == job_id for r in rows)
    # Critique rows have NO recording user (machine-author).
    assert all(r.recorded_by_user_id is None for r in rows)
    # Critique rows are lesson-level (quiz_item_id IS NULL).
    assert all(r.quiz_item_id is None for r in rows)


# ── 2. Multi-lesson ingestion fans out per-lesson rows ─────────────────────


async def test_persist_fans_out_across_multiple_lessons(db_session):
    deck = await _seed_deck(db_session)
    lesson_a = await _seed_lesson(db_session, deck.id)
    lesson_b = await _seed_lesson(db_session, deck.id)
    critique = _make_critique(
        {"accuracy": 4, "clarity": 4, "completeness": 4, "cohesion": 4}
    )

    written = await critique_signal_consumer.persist_critique_signals(
        lesson_ids=[lesson_a.id, lesson_b.id],
        critique=critique,
        job_id="job-multi",
        db=db_session,
    )

    assert written == 8  # 4 dims × 2 lessons
    for lid in (lesson_a.id, lesson_b.id):
        rows = (
            await db_session.execute(
                select(CardQualitySignal).where(
                    CardQualitySignal.lesson_id == lid,
                    CardQualitySignal.signal_source == "critique",
                )
            )
        ).scalars().all()
        assert len(rows) == 4


# ── 3. AC-10: idempotent re-run ────────────────────────────────────────────


async def test_persist_is_idempotent_on_replay(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    critique = _make_critique(
        {"accuracy": 4, "clarity": 5, "completeness": 3, "cohesion": 5}
    )

    first = await critique_signal_consumer.persist_critique_signals(
        lesson_ids=[lesson.id],
        critique=critique,
        job_id="job-1",
        db=db_session,
    )
    second = await critique_signal_consumer.persist_critique_signals(
        lesson_ids=[lesson.id],
        critique=critique,
        job_id="job-1",
        db=db_session,
    )

    assert first == 4
    assert second == 4  # writes counter — UPSERT executed
    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.lesson_id == lesson.id,
                CardQualitySignal.signal_source == "critique",
            )
        )
    ).scalars().all()
    assert len(rows) == 4  # but only 4 rows exist (UPSERT, not INSERT-twice)


# ── 4. Empty inputs are no-op safe ─────────────────────────────────────────


async def test_persist_empty_lesson_list_returns_zero(db_session):
    critique = _make_critique({"accuracy": 4})
    written = await critique_signal_consumer.persist_critique_signals(
        lesson_ids=[],
        critique=critique,
        job_id="job-empty",
        db=db_session,
    )
    assert written == 0


async def test_persist_critique_with_no_dimensions_returns_zero(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    critique = CritiqueSchema(
        verdict="PASS", rationale="empty", dimensions=[]
    )
    written = await critique_signal_consumer.persist_critique_signals(
        lesson_ids=[lesson.id],
        critique=critique,
        job_id="job-nodim",
        db=db_session,
    )
    assert written == 0
