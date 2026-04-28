"""Smoke tests on the canonical Phase 6 seed corpus.

Spec: docs/specs/phase-6/05-seed-lessons.md §10.3, AC-1, AC-8.

These tests load the **actual** committed corpus under
``app/data/decks/seed_lessons/`` (not synthetic fixtures) and assert:

- D-1 invariants: 12 decks × 2 lessons = 24 lessons.
- AC-8 enum coverage: all ``persona_visibility`` values, both ``tier``
  values, all ``question_type`` values, all ``difficulty`` values.

Failure here means the canonical corpus drifted away from the spec —
either a deck was added/removed, or coverage of an enum value was lost.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.services.seed_lessons_service import load_seed_corpus


@pytest_asyncio.fixture(loop_scope="session")
async def canonical_corpus_db(db_session):
    """Truncate curriculum tables then load the canonical seed corpus."""

    async def _truncate() -> None:
        await db_session.execute(
            text(
                "TRUNCATE TABLE quiz_item_progress, quiz_items, lessons, decks "
                "RESTART IDENTITY CASCADE"
            )
        )
        await db_session.commit()

    await _truncate()
    await load_seed_corpus(db_session)
    try:
        yield db_session
    finally:
        await _truncate()


@pytest.mark.asyncio(loop_scope="session")
async def test_canonical_seed_corpus_count_invariants(canonical_corpus_db) -> None:
    decks = (await canonical_corpus_db.execute(select(Deck))).scalars().all()
    assert len(decks) == 12, f"Expected 12 decks per D-1; got {len(decks)}"

    lessons = (await canonical_corpus_db.execute(select(Lesson))).scalars().all()
    assert len(lessons) == 24, f"Expected 24 lessons (12 decks × 2 per D-1); got {len(lessons)}"

    quizzes = (await canonical_corpus_db.execute(select(QuizItem))).scalars().all()
    assert 24 <= len(quizzes) <= 96, (
        f"Expected 24-96 quiz_items; got {len(quizzes)}"
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_canonical_seed_corpus_satisfies_ac8(canonical_corpus_db) -> None:
    decks = (await canonical_corpus_db.execute(select(Deck))).scalars().all()
    personas = {d.persona_visibility for d in decks}
    assert personas == {"climber", "interview_prepper", "both"}, (
        f"AC-8: persona_visibility must cover all 3 values; got {personas}"
    )
    tiers = {d.tier for d in decks}
    assert tiers == {"foundation", "premium"}, (
        f"AC-8: tier must cover both values; got {tiers}"
    )

    quizzes = (await canonical_corpus_db.execute(select(QuizItem))).scalars().all()
    qtypes = {q.question_type for q in quizzes}
    assert qtypes == {"mcq", "free_text", "code_completion"}, (
        f"AC-8: question_type must cover all 3 values; got {qtypes}"
    )
    difficulties = {q.difficulty for q in quizzes}
    assert difficulties == {"easy", "medium", "hard"}, (
        f"AC-8: difficulty must cover all 3 values; got {difficulties}"
    )
