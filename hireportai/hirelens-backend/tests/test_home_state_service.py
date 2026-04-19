"""Unit tests for the home state evaluator (P5-S18c, spec #40 §9).

Each test seeds the precise trigger condition for one state and asserts
that the evaluator emits (or suppresses) the expected state name. Cache
behavior and partial-failure paths are covered with a stubbed Redis.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.gamification import GamificationStats, UserBadge
from app.models.mission import Mission
from app.models.subscription import Subscription
from app.models.tracker import TrackerApplicationModel
from app.models.user import User
from app.services import home_state_service
from app.services.home_state_service import (
    CACHE_KEY_PREFIX,
    HomeStateResponse,
    evaluate_state,
    invalidate,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Fake redis ───────────────────────────────────────────────────────────────


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.set_calls: int = 0
        self.get_calls: int = 0

    def get(self, key: str) -> Optional[str]:
        self.get_calls += 1
        return self.store.get(key)

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.set_calls += 1
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.store.pop(key, None)

    def ping(self) -> bool:
        return True


# ── Seed helpers ─────────────────────────────────────────────────────────────


async def _seed_user(db: AsyncSession, *, persona: str = "career_climber") -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@home-test.com",
        name="Home Tester",
        persona=persona,
        onboarding_completed=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _seed_stats(
    db: AsyncSession,
    user_id: str,
    *,
    current_streak: int = 0,
    longest_streak: int = 0,
    last_active_date: Optional[date] = None,
) -> GamificationStats:
    stats = GamificationStats(
        user_id=user_id,
        current_streak=current_streak,
        longest_streak=longest_streak,
        last_active_date=last_active_date,
        total_xp=0,
        freezes_available=0,
    )
    db.add(stats)
    await db.flush()
    return stats


async def _seed_card_progress(
    db: AsyncSession,
    user_id: str,
    *,
    last_reviewed: Optional[datetime] = None,
    reps: int = 0,
) -> CardProgress:
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"Cat-{uuid.uuid4().hex[:6]}",
        icon="📚",
        color="from-blue-500 to-indigo-600",
        display_order=99,
        source="foundation",
    )
    db.add(cat)
    await db.flush()
    card = Card(
        id=str(uuid.uuid4()),
        category_id=cat.id,
        question="Q?",
        answer="A.",
        difficulty="medium",
        tags=[],
    )
    db.add(card)
    await db.flush()
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
        last_reviewed=last_reviewed,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(cp)
    await db.flush()
    return cp


async def _seed_active_mission(
    db: AsyncSession,
    user_id: str,
    *,
    target_date: date,
) -> Mission:
    mission = Mission(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title="Home test mission",
        target_date=target_date,
        daily_target=5,
        status="active",
    )
    db.add(mission)
    await db.flush()
    return mission


async def _seed_tracker_scan(
    db: AsyncSession, user_id: str, *, created_at: Optional[datetime] = None
) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company="Acme",
        role="Engineer",
        date_applied=date.today().isoformat(),
        ats_score=75,
        scan_id=str(uuid.uuid4()),
    )
    db.add(row)
    await db.flush()
    if created_at is not None:
        # tracker.created_at uses server_default=func.now(); override after flush.
        row.created_at = created_at
        await db.flush()
    return row


async def _seed_first_review_badge(db: AsyncSession, user_id: str) -> None:
    ub = UserBadge(
        id=str(uuid.uuid4()),
        user_id=user_id,
        badge_id="first_review",
    )
    db.add(ub)
    await db.flush()


async def _seed_subscription(
    db: AsyncSession, user_id: str, *, plan: str = "free"
) -> None:
    sub = Subscription(user_id=user_id, plan=plan, status="active")
    db.add(sub)
    await db.flush()


# ── Per-state happy/negative tests ───────────────────────────────────────────


class TestStreakAtRisk:
    async def test_streak_at_risk_when_dormant_19h_with_streak_3(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_stats(
            db_session,
            user.id,
            current_streak=3,
            longest_streak=5,
            last_active_date=date.today(),
        )
        await _seed_card_progress(
            db_session,
            user.id,
            last_reviewed=datetime.now(timezone.utc) - timedelta(hours=19),
            reps=10,  # not first_session_done
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "streak_at_risk" in resp.states

    async def test_streak_at_risk_NOT_when_recent_review(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_stats(
            db_session,
            user.id,
            current_streak=5,
            longest_streak=5,
            last_active_date=date.today(),
        )
        await _seed_card_progress(
            db_session,
            user.id,
            last_reviewed=datetime.now(timezone.utc) - timedelta(hours=2),
            reps=10,
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "streak_at_risk" not in resp.states

    async def test_streak_at_risk_NOT_when_streak_below_3(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_stats(db_session, user.id, current_streak=2)
        await _seed_card_progress(
            db_session,
            user.id,
            last_reviewed=datetime.now(timezone.utc) - timedelta(hours=20),
            reps=10,
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "streak_at_risk" not in resp.states


class TestMissionStates:
    async def test_mission_active_when_mission_in_flight(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_active_mission(
            db_session, user.id, target_date=date.today() + timedelta(days=5)
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "mission_active" in resp.states
        assert "mission_overdue" not in resp.states

    async def test_mission_overdue_overrides_mission_active(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_active_mission(
            db_session, user.id, target_date=date.today() - timedelta(days=1)
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "mission_overdue" in resp.states
        assert "mission_active" not in resp.states


class TestResumeStale:
    async def test_resume_stale_when_last_scan_30d_ago(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_tracker_scan(
            db_session,
            user.id,
            created_at=datetime.utcnow() - timedelta(days=30),
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "resume_stale" in resp.states

    async def test_resume_stale_NOT_when_recent_scan(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_tracker_scan(
            db_session,
            user.id,
            created_at=datetime.utcnow() - timedelta(days=2),
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "resume_stale" not in resp.states


class TestInactiveReturner:
    async def test_inactive_returner_in_7_to_30d_window(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_stats(
            db_session,
            user.id,
            current_streak=0,
            longest_streak=10,
            last_active_date=date.today() - timedelta(days=10),
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "inactive_returner" in resp.states

    async def test_inactive_returner_NOT_outside_window(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_stats(
            db_session,
            user.id,
            current_streak=0,
            longest_streak=10,
            last_active_date=date.today() - timedelta(days=45),
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "inactive_returner" not in resp.states


class TestFirstSessionDone:
    async def test_first_session_done_via_badge_and_reps_cap(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_first_review_badge(db_session, user.id)
        await _seed_card_progress(
            db_session,
            user.id,
            last_reviewed=datetime.now(timezone.utc) - timedelta(hours=1),
            reps=2,
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "first_session_done" in resp.states

    async def test_first_session_done_NOT_when_reps_exceed_3(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_first_review_badge(db_session, user.id)
        await _seed_card_progress(
            db_session,
            user.id,
            last_reviewed=datetime.now(timezone.utc) - timedelta(hours=1),
            reps=5,
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "first_session_done" not in resp.states


# ── Priority + mutual exclusion ──────────────────────────────────────────────


class TestPriorityAndExclusion:
    async def test_priority_ordering_deterministic(
        self, db_session: AsyncSession
    ):
        """Streak-at-risk + resume_stale → streak_at_risk first (priority 2 vs 4)."""
        user = await _seed_user(db_session)
        await _seed_stats(
            db_session,
            user.id,
            current_streak=4,
            longest_streak=4,
            last_active_date=date.today(),
        )
        await _seed_card_progress(
            db_session,
            user.id,
            last_reviewed=datetime.now(timezone.utc) - timedelta(hours=20),
            reps=10,
        )
        await _seed_tracker_scan(
            db_session,
            user.id,
            created_at=datetime.utcnow() - timedelta(days=30),
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert resp.states[0] == "streak_at_risk"
        assert "resume_stale" in resp.states
        # streak_at_risk has lower priority number than resume_stale
        assert resp.states.index("streak_at_risk") < resp.states.index(
            "resume_stale"
        )

    async def test_mutually_exclusive_mission_states_never_coexist(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_active_mission(
            db_session, user.id, target_date=date.today() - timedelta(days=2)
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert ("mission_active" in resp.states) ^ (
            "mission_overdue" in resp.states
        )

    async def test_inactive_beats_first_session_when_both_match(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        # First-session signals
        await _seed_first_review_badge(db_session, user.id)
        await _seed_card_progress(
            db_session,
            user.id,
            last_reviewed=datetime.now(timezone.utc) - timedelta(days=10),
            reps=1,
        )
        # Inactive-returner signals
        await _seed_stats(
            db_session,
            user.id,
            current_streak=0,
            longest_streak=2,
            last_active_date=date.today() - timedelta(days=10),
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert "inactive_returner" in resp.states
        assert "first_session_done" not in resp.states


# ── Cache ────────────────────────────────────────────────────────────────────


class TestCache:
    async def test_cache_hit_skips_recompute(self, db_session: AsyncSession):
        user = await _seed_user(db_session)
        r = FakeRedis()
        # Pre-populate the cache with a sentinel response that doesn't match
        # what compute would produce.
        sentinel = HomeStateResponse(
            persona="career_climber", states=["sentinel_only"]
        )
        r.store[f"{CACHE_KEY_PREFIX}{user.id}"] = sentinel.model_dump_json()

        resp = await evaluate_state(user, db_session, r=r)
        assert resp.states == ["sentinel_only"]
        # No write should have happened since cache hit.
        assert r.set_calls == 0

    async def test_cache_miss_computes_and_sets(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        r = FakeRedis()
        await evaluate_state(user, db_session, r=r)
        assert r.set_calls == 1
        assert f"{CACHE_KEY_PREFIX}{user.id}" in r.store

    async def test_invalidate_deletes_cache(self, db_session: AsyncSession):
        user = await _seed_user(db_session)
        r = FakeRedis()
        await evaluate_state(user, db_session, r=r)
        assert f"{CACHE_KEY_PREFIX}{user.id}" in r.store
        invalidate(user.id, r=r)
        assert f"{CACHE_KEY_PREFIX}{user.id}" not in r.store


# ── Partial-failure ─────────────────────────────────────────────────────────


class TestPartialFailure:
    async def test_partial_failure_returns_empty_states(
        self, db_session: AsyncSession, monkeypatch
    ):
        """If _compute_state_uncached raises, we return empty states + persona."""
        user = await _seed_user(db_session)
        r = FakeRedis()

        async def _boom(*_args, **_kwargs):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(
            home_state_service, "_compute_state_uncached", _boom
        )

        resp = await evaluate_state(user, db_session, r=r)
        assert resp.states == []
        assert resp.persona == user.persona


# ── Empty-state engaged user ────────────────────────────────────────────────


class TestEmptyStateForEngagedUser:
    async def test_engaged_user_has_no_active_states(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session)
        await _seed_stats(
            db_session,
            user.id,
            current_streak=10,
            longest_streak=10,
            last_active_date=date.today(),
        )
        await _seed_card_progress(
            db_session,
            user.id,
            last_reviewed=datetime.now(timezone.utc) - timedelta(hours=2),
            reps=50,
        )
        r = FakeRedis()
        resp = await evaluate_state(user, db_session, r=r)
        assert resp.states == []
