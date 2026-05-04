"""Unit tests for `loop_progress_service.get_loop_progress` (spec #66 §6.1).

Mirrors the test_home_state_service seed-helper pattern.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.tracker import TrackerApplicationModel
from app.models.tracker_application_score import TrackerApplicationScore
from app.models.user import User
from app.services.loop_progress_service import (
    TrackerNotFoundError,
    get_loop_progress,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_user(db: AsyncSession) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@loop-test.com",
        name="Loop Tester",
        persona="interview_prepper",
        onboarding_completed=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _seed_tracker(
    db: AsyncSession,
    user_id: str,
    *,
    skills_missing: list[str] | None = None,
) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company="Acme",
        role="Engineer",
        date_applied=date.today().isoformat(),
        ats_score=72,
        scan_id=str(uuid.uuid4()),
        skills_missing=json.dumps(skills_missing) if skills_missing else None,
    )
    db.add(row)
    await db.flush()
    return row


async def _seed_category_with_cards(
    db: AsyncSession, *, name: str, card_count: int
) -> tuple[Category, list[Card]]:
    cat = Category(
        id=str(uuid.uuid4()),
        name=name,
        icon="📚",
        color="from-blue-500 to-indigo-600",
        display_order=0,
        source="foundation",
    )
    db.add(cat)
    await db.flush()
    cards: list[Card] = []
    for _ in range(card_count):
        card = Card(
            id=str(uuid.uuid4()),
            category_id=cat.id,
            question="Q?",
            answer="A.",
            difficulty="medium",
            tags=[],
        )
        db.add(card)
        cards.append(card)
    await db.flush()
    return cat, cards


async def _seed_card_progress(
    db: AsyncSession, user_id: str, card: Card, *, reps: int = 1
) -> None:
    cp = CardProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        card_id=card.id,
        state="review",
        stability=5.0,
        difficulty_fsrs=5.0,
        elapsed_days=0.0,
        scheduled_days=5.0,
        reps=reps,
        lapses=0,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(cp)
    await db.flush()


async def _seed_tracker_score(
    db: AsyncSession,
    *,
    tracker_id: str,
    user_id: str,
    scanned_at: datetime,
) -> None:
    row = TrackerApplicationScore(
        id=str(uuid.uuid4()),
        tracker_application_id=tracker_id,
        user_id=user_id,
        scan_id=str(uuid.uuid4()),
        overall_score=72,
        keyword_match_score=70.0,
        skills_coverage_score=65.0,
        formatting_compliance_score=80.0,
        bullet_strength_score=72.0,
        jd_hash="a" * 64,
        resume_hash="b" * 64,
        scanned_at=scanned_at,
    )
    db.add(row)
    await db.flush()


# ── 1. Tracker not found / cross-user ────────────────────────────────────────


async def test_get_loop_progress_unknown_tracker_raises(db_session):
    user = await _seed_user(db_session)
    with pytest.raises(TrackerNotFoundError):
        await get_loop_progress(db_session, user.id, str(uuid.uuid4()))


async def test_get_loop_progress_cross_user_tracker_raises(db_session):
    user_a = await _seed_user(db_session)
    user_b = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user_a.id)
    with pytest.raises(TrackerNotFoundError):
        await get_loop_progress(db_session, user_b.id, tracker.id)


# ── 2. Empty skills_missing → zero gaps, zero reviewed ──────────────────────


async def test_get_loop_progress_zero_gap_returns_zero_counts(db_session):
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user.id, skills_missing=None)

    resp = await get_loop_progress(db_session, user.id, tracker.id)

    assert resp.tracker_application_id == tracker.id
    assert resp.total_gap_cards == 0
    assert resp.reviewed_gap_cards == 0
    assert resp.percent_reviewed == 0.0
    assert resp.days_since_last_scan is None


# ── 3. Gap-card count + percent_reviewed math ───────────────────────────────


async def test_get_loop_progress_counts_cards_and_reviewed(db_session):
    user = await _seed_user(db_session)
    # "Python" maps to "Technical" category per skill_taxonomy.
    tracker = await _seed_tracker(db_session, user.id, skills_missing=["Python"])
    _, cards = await _seed_category_with_cards(
        db_session, name="Technical", card_count=4
    )
    # 2 of 4 cards reviewed (reps > 0)
    await _seed_card_progress(db_session, user.id, cards[0], reps=1)
    await _seed_card_progress(db_session, user.id, cards[1], reps=3)

    resp = await get_loop_progress(db_session, user.id, tracker.id)

    assert resp.total_gap_cards == 4
    assert resp.reviewed_gap_cards == 2
    assert resp.percent_reviewed == 50.0


async def test_get_loop_progress_excludes_unreviewed_progress_rows(db_session):
    """A CardProgress row with reps=0 must NOT count as reviewed."""
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user.id, skills_missing=["Python"])
    _, cards = await _seed_category_with_cards(
        db_session, name="Technical", card_count=2
    )
    await _seed_card_progress(db_session, user.id, cards[0], reps=0)

    resp = await get_loop_progress(db_session, user.id, tracker.id)

    assert resp.total_gap_cards == 2
    assert resp.reviewed_gap_cards == 0
    assert resp.percent_reviewed == 0.0


# ── 4. days_since_last_scan derivation ──────────────────────────────────────


async def test_get_loop_progress_days_since_last_scan_from_scores_table(
    db_session,
):
    user = await _seed_user(db_session)
    tracker = await _seed_tracker(db_session, user.id)
    five_days_ago = datetime.now(timezone.utc) - timedelta(days=5, hours=1)
    await _seed_tracker_score(
        db_session,
        tracker_id=tracker.id,
        user_id=user.id,
        scanned_at=five_days_ago,
    )

    resp = await get_loop_progress(db_session, user.id, tracker.id)

    assert resp.days_since_last_scan == 5
