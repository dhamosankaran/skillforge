"""Tests for ``career_intent_service`` and ``schemas/career_intent`` (B-125a).

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §6.1 + §5.4 +
§10.1 + §11 AC-1..AC-7.

Covers:

- Model column shape + FK CASCADE.
- ``set_intent`` insert + supersede semantics (AC-1, AC-2).
- ``get_current_intent`` (AC-3).
- ``clear_intent`` (AC-4).
- ``get_aggregate_stats`` cohort-size threshold + bucket isolation
  (AC-5, AC-6, AC-7).
- ``CareerIntentCreate`` validators — past-quarter rejection + bad role
  rejection (mirror AC-10, AC-11 at the schema level).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from pydantic import ValidationError

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.user import User
from app.models.user_career_intent import UserCareerIntent
from app.schemas.career_intent import (
    CareerIntentCreate,
    _current_quarter_tuple,
)
from app.services import career_intent_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ────────────────────────────────────────────────────────────


async def _seed_user(db_session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        name="CC User",
        persona="career_climber",
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _future_quarter() -> str:
    """Return a quarter string guaranteed to validate as 'future'."""
    year, q = _current_quarter_tuple()
    if q == 4:
        return f"{year + 1}-Q1"
    return f"{year}-Q{q + 1}"


async def _seed_cohort(
    db_session, *, count: int, role: str, quarter: str
) -> list[User]:
    users = []
    for _ in range(count):
        user = await _seed_user(db_session)
        await career_intent_service.set_intent(
            db_session, user.id, role, quarter
        )
        users.append(user)
    return users


async def _seed_category_with_card(db_session, *, name: str) -> tuple[Category, Card]:
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"{name}-{uuid.uuid4().hex[:6]}",
        icon="📚",
        color="#000000",
        display_order=0,
        source="seed",
    )
    db_session.add(cat)
    await db_session.flush()
    card = Card(
        id=str(uuid.uuid4()),
        category_id=cat.id,
        question="Q?",
        answer="A.",
        difficulty="medium",
    )
    db_session.add(card)
    await db_session.flush()
    return cat, card


async def _seed_progress(
    db_session, *, user_id: str, card_id: str, reps: int
) -> CardProgress:
    cp = CardProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        card_id=card_id,
        state="review",
        stability=1.0,
        difficulty_fsrs=5.0,
        due_date=datetime.now(timezone.utc),
        reps=reps,
        lapses=0,
    )
    db_session.add(cp)
    await db_session.flush()
    return cp


# ── 1. Model shape (AC-1) ───────────────────────────────────────────────────


async def test_user_career_intent_row_persists_with_defaults(db_session):
    user = await _seed_user(db_session)
    quarter = _future_quarter()

    intent = UserCareerIntent(
        user_id=user.id,
        target_role="staff",
        target_quarter=quarter,
    )
    db_session.add(intent)
    await db_session.flush()
    await db_session.refresh(intent)

    assert intent.id is not None
    assert intent.user_id == user.id
    assert intent.target_role == "staff"
    assert intent.target_quarter == quarter
    assert intent.created_at is not None
    assert intent.superseded_at is None


# ── 2. set_intent insert + supersede (AC-2) ─────────────────────────────────


async def test_set_intent_creates_first_row_with_null_supersede(db_session):
    user = await _seed_user(db_session)
    quarter = _future_quarter()

    intent = await career_intent_service.set_intent(
        db_session, user.id, "staff", quarter
    )
    assert intent.superseded_at is None
    assert intent.target_role == "staff"
    assert intent.target_quarter == quarter


async def test_set_intent_supersedes_prior_current_row(db_session):
    user = await _seed_user(db_session)
    q = _future_quarter()

    first = await career_intent_service.set_intent(
        db_session, user.id, "staff", q
    )
    second = await career_intent_service.set_intent(
        db_session, user.id, "principal", q
    )

    rows = (
        await db_session.execute(
            select(UserCareerIntent)
            .where(UserCareerIntent.user_id == user.id)
            .order_by(UserCareerIntent.created_at.asc())
        )
    ).scalars().all()
    assert len(rows) == 2
    # First row was superseded (stamp was set)
    await db_session.refresh(first)
    assert first.superseded_at is not None
    # Second row is the new current
    assert second.superseded_at is None
    assert second.target_role == "principal"


# ── 3. get_current_intent (AC-3) ────────────────────────────────────────────


async def test_get_current_intent_returns_none_when_no_row(db_session):
    user = await _seed_user(db_session)
    assert (
        await career_intent_service.get_current_intent(db_session, user.id)
    ) is None


async def test_get_current_intent_returns_only_current_after_history(db_session):
    user = await _seed_user(db_session)
    q = _future_quarter()

    await career_intent_service.set_intent(db_session, user.id, "staff", q)
    await career_intent_service.set_intent(db_session, user.id, "em", q)
    await career_intent_service.set_intent(db_session, user.id, "principal", q)

    current = await career_intent_service.get_current_intent(
        db_session, user.id
    )
    assert current is not None
    assert current.target_role == "principal"
    assert current.superseded_at is None


# ── 4. clear_intent (AC-4) ──────────────────────────────────────────────────


async def test_clear_intent_stamps_current_row_and_returns_true(db_session):
    user = await _seed_user(db_session)
    q = _future_quarter()
    await career_intent_service.set_intent(db_session, user.id, "staff", q)

    cleared = await career_intent_service.clear_intent(db_session, user.id)
    assert cleared is True

    current = await career_intent_service.get_current_intent(
        db_session, user.id
    )
    assert current is None


async def test_clear_intent_no_op_when_nothing_to_clear(db_session):
    user = await _seed_user(db_session)
    cleared = await career_intent_service.clear_intent(db_session, user.id)
    assert cleared is False


# ── 5. get_aggregate_stats threshold + isolation (AC-5/6/7) ─────────────────


# Aggregate-stats tests use distant-future quarters that no other test
# touches — sibling test files (test_career_intent_route.py) commit rows
# at ``_future_quarter()`` which would otherwise leak into the cohort
# count via the session-scoped engine.


async def test_aggregate_stats_returns_none_below_threshold(db_session):
    quarter = "2099-Q1"
    # 9 users — one short of the 10-cohort floor.
    cohort = await _seed_cohort(
        db_session, count=9, role="senior_staff", quarter=quarter
    )
    _, card = await _seed_category_with_card(db_session, name="rag")
    for u in cohort:
        await _seed_progress(db_session, user_id=u.id, card_id=card.id, reps=5)

    stats = await career_intent_service.get_aggregate_stats(
        db_session, "senior_staff", quarter
    )
    assert stats is None


async def test_aggregate_stats_at_threshold_returns_top_categories(db_session):
    quarter = "2099-Q2"
    cohort = await _seed_cohort(
        db_session, count=10, role="sr_em", quarter=quarter
    )
    _, card_a = await _seed_category_with_card(db_session, name="system_design")
    _, card_b = await _seed_category_with_card(db_session, name="distributed")
    _, card_c = await _seed_category_with_card(db_session, name="agentic_ai")
    _, card_d = await _seed_category_with_card(db_session, name="other")
    # Seed reps weighted toward system_design > distributed > agentic_ai.
    for u in cohort:
        await _seed_progress(db_session, user_id=u.id, card_id=card_a.id, reps=10)
        await _seed_progress(db_session, user_id=u.id, card_id=card_b.id, reps=6)
        await _seed_progress(db_session, user_id=u.id, card_id=card_c.id, reps=4)
        await _seed_progress(db_session, user_id=u.id, card_id=card_d.id, reps=1)

    stats = await career_intent_service.get_aggregate_stats(
        db_session, "sr_em", quarter
    )
    assert stats is not None
    assert stats.cohort_size == 10
    assert stats.target_role == "sr_em"
    assert stats.target_quarter == quarter
    # Top-K cap respected.
    assert len(stats.top_categories) == career_intent_service.TOP_CATEGORIES_K
    # Top-1 has the highest share.
    top_share = stats.top_categories[0].percent_of_study_time
    assert top_share > stats.top_categories[1].percent_of_study_time


async def test_aggregate_stats_isolates_by_bucket(db_session):
    quarter = "2099-Q3"
    # 10 users in (distinguished, 2099-Q3) — meets threshold.
    bucket_a_users = await _seed_cohort(
        db_session, count=10, role="distinguished", quarter=quarter
    )
    # 5 users in (em, 2099-Q3) — below threshold.
    bucket_b_users = await _seed_cohort(
        db_session, count=5, role="em", quarter=quarter
    )
    _, card = await _seed_category_with_card(db_session, name="design")
    for u in bucket_a_users + bucket_b_users:
        await _seed_progress(db_session, user_id=u.id, card_id=card.id, reps=5)

    bucket_a_stats = await career_intent_service.get_aggregate_stats(
        db_session, "distinguished", quarter
    )
    bucket_b_stats = await career_intent_service.get_aggregate_stats(
        db_session, "em", quarter
    )

    assert bucket_a_stats is not None
    assert bucket_a_stats.cohort_size == 10
    assert bucket_b_stats is None


async def test_aggregate_stats_zero_reps_returns_none(db_session):
    """At threshold but with zero study activity → None (no copy this tick)."""
    quarter = "2099-Q4"
    await _seed_cohort(
        db_session, count=10, role="director", quarter=quarter
    )
    stats = await career_intent_service.get_aggregate_stats(
        db_session, "director", quarter
    )
    assert stats is None


# ── 6. Schema validation (AC-10 / AC-11 mirrors) ────────────────────────────


def test_schema_rejects_bad_role():
    with pytest.raises(ValidationError):
        CareerIntentCreate(target_role="vp", target_quarter="2099-Q1")


def test_schema_rejects_past_quarter():
    with pytest.raises(ValidationError):
        CareerIntentCreate(target_role="staff", target_quarter="2020-Q1")


def test_schema_accepts_valid_payload():
    # Use a far-future quarter so the test stays valid for years.
    body = CareerIntentCreate(
        target_role="principal", target_quarter="2099-Q4"
    )
    assert body.target_role == "principal"
    assert body.target_quarter == "2099-Q4"
