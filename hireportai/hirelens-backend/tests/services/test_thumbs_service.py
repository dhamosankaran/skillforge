"""Service tests for ``thumbs_service`` (Phase 6 slice 6.13.5b).

Spec: docs/specs/phase-6/12-quality-signals.md §6.3 + §11 AC-7 / AC-8 +
§12 D-5 / D-7 / D-8 / D-11.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.card_quality_signal import CardQualitySignal
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.user import User
from app.services import thumbs_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ────────────────────────────────────────────────────────────


async def _seed_deck(
    db_session,
    *,
    persona_visibility: str = "both",
    tier: str = "foundation",
    archived: bool = False,
) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=f"thumb-deck-{uuid.uuid4().hex[:8]}",
        title="Thumb Deck",
        description="seed",
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
    archived: bool = False,
    published: bool = True,
) -> Lesson:
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Thumb Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=(
            datetime.now(timezone.utc) if published else None
        ),
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _seed_user(db_session, *, persona: str | None = None) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        email=f"u-{uuid.uuid4().hex[:8]}@example.com",
        name="Thumb User",
        persona=persona,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ── 1. AC-7: happy path returns ThumbsResponse + persists row ──────────────


async def test_submit_thumbs_persists_row_and_returns_response(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    user = await _seed_user(db_session)

    response = await thumbs_service.submit_thumbs(
        lesson_id=lesson.id, score=1, user=user, db=db_session
    )

    assert response.accepted is True
    assert response.score == 1
    assert response.aggregate_score == 1.0
    assert response.aggregate_count == 1

    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.lesson_id == lesson.id,
                CardQualitySignal.signal_source == "user_thumbs",
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert float(rows[0].score) == 1.0
    assert rows[0].recorded_by_user_id == user.id


# ── 2. UPSERT idempotency (§12 D-8) — same score is no-op for row count ────


async def test_resubmit_same_score_keeps_one_row(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    user = await _seed_user(db_session)

    await thumbs_service.submit_thumbs(
        lesson_id=lesson.id, score=1, user=user, db=db_session
    )
    await thumbs_service.submit_thumbs(
        lesson_id=lesson.id, score=1, user=user, db=db_session
    )

    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.lesson_id == lesson.id,
                CardQualitySignal.recorded_by_user_id == user.id,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert float(rows[0].score) == 1.0


# ── 3. Reverse vote overwrites on the same row ──────────────────────────────


async def test_resubmit_reverse_score_overwrites_row(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    user = await _seed_user(db_session)

    await thumbs_service.submit_thumbs(
        lesson_id=lesson.id, score=1, user=user, db=db_session
    )
    response = await thumbs_service.submit_thumbs(
        lesson_id=lesson.id, score=-1, user=user, db=db_session
    )

    assert response.score == -1
    assert response.aggregate_score == -1.0
    rows = (
        await db_session.execute(
            select(CardQualitySignal).where(
                CardQualitySignal.lesson_id == lesson.id,
                CardQualitySignal.recorded_by_user_id == user.id,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert float(rows[0].score) == -1.0


# ── 4. Aggregate averages across users ──────────────────────────────────────


async def test_aggregate_combines_thumbs_across_users(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id)
    a = await _seed_user(db_session)
    b = await _seed_user(db_session)
    c = await _seed_user(db_session)

    await thumbs_service.submit_thumbs(
        lesson_id=lesson.id, score=1, user=a, db=db_session
    )
    await thumbs_service.submit_thumbs(
        lesson_id=lesson.id, score=1, user=b, db=db_session
    )
    response = await thumbs_service.submit_thumbs(
        lesson_id=lesson.id, score=-1, user=c, db=db_session
    )

    # Three distinct rows, mean = (1 + 1 + -1) / 3
    assert response.aggregate_count == 3
    assert response.aggregate_score == pytest.approx(1.0 / 3, abs=1e-6)


# ── 5. AC-6: archived lesson surfaces LessonNotVisibleError → 404 ──────────


async def test_archived_lesson_raises_not_visible(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id, archived=True)
    user = await _seed_user(db_session)

    with pytest.raises(thumbs_service.LessonNotVisibleError):
        await thumbs_service.submit_thumbs(
            lesson_id=lesson.id, score=1, user=user, db=db_session
        )


async def test_unpublished_lesson_raises_not_visible(db_session):
    deck = await _seed_deck(db_session)
    lesson = await _seed_lesson(db_session, deck.id, published=False)
    user = await _seed_user(db_session)

    with pytest.raises(thumbs_service.LessonNotVisibleError):
        await thumbs_service.submit_thumbs(
            lesson_id=lesson.id, score=1, user=user, db=db_session
        )


async def test_unknown_lesson_raises_not_visible(db_session):
    user = await _seed_user(db_session)
    with pytest.raises(thumbs_service.LessonNotVisibleError):
        await thumbs_service.submit_thumbs(
            lesson_id="missing-id", score=1, user=user, db=db_session
        )
