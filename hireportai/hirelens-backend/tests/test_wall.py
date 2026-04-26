"""Tests for the free-tier daily-card review wall (spec #50).

The wall enforces LD-001: free-plan users get
``Settings.free_daily_review_limit`` card reviews per day (default 10
per LD-001 amendment 2026-04-26; was 15 prior), resetting at the
user's local midnight (timezone from ``EmailPreference.timezone``,
default UTC). Pro/Enterprise/admin bypass. Implemented by
``study_service._check_daily_wall`` using Redis INCR keyed by
``daily_cards:{user_id}:{YYYY-MM-DD}``. Fails open on Redis outage
(counter skipped; ``counter_unavailable=True`` analytics marker).

Tests map 1:1 to the spec's §Test Plan → Backend pytest list. Boundary
counts derive from ``settings.free_daily_review_limit`` so the suite
follows the LD-001 default and the LD-A1 env-override hook.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.config import get_settings
from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.email_preference import EmailPreference
from app.models.gamification import GamificationStats
from app.models.subscription import Subscription
from app.models.user import User
from app.services import study_service
from app.services.study_service import DailyReviewLimitError

# Active cap for boundary-derived assertions. Reads ``Settings`` so the
# suite follows the LD-001 amendment 2026-04-26 (15 → 10) and any
# future env-override at process start.
CAP = get_settings().free_daily_review_limit

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── FakeRedis (mirrors test_home_state_service.py pattern) ──────────────────


class FakeRedis:
    """Minimal Redis stub supporting INCR/EXPIRE/GET/DELETE semantics.

    ``incr`` is atomic wrt asyncio concurrency because Python's GIL
    serialises the read-modify-write on a plain dict.
    """

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.incr_calls: int = 0

    def incr(self, key: str) -> int:
        self.incr_calls += 1
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key: str, ttl_seconds: int) -> None:
        self.ttls[key] = ttl_seconds

    def get(self, key: str) -> Optional[str]:
        val = self.store.get(key)
        return str(val) if val is not None else None

    def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.ttls.pop(key, None)

    def ping(self) -> bool:
        return True


# ── Seed helpers ────────────────────────────────────────────────────────────


async def _make_user(
    db,
    *,
    plan: str = "free",
    sub_status: str = "active",
    role: str = "user",
    timezone_str: Optional[str] = None,
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@wall-test.com",
        name="Wall Tester",
        role=role,
    )
    db.add(user)
    await db.flush()

    sub = Subscription(user_id=user.id, plan=plan, status=sub_status)
    db.add(sub)
    await db.flush()
    await db.refresh(user, attribute_names=["subscription"])

    if timezone_str is not None:
        pref = EmailPreference(user_id=user.id, timezone=timezone_str)
        db.add(pref)
        await db.flush()

    return user


async def _make_card(db, *, source: str = "foundation") -> Card:
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"Cat-{uuid.uuid4().hex[:6]}",
        icon="📚",
        color="c",
        display_order=99,
        source=source,
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
    return card


async def _submit(
    db,
    user: User,
    card_id: str,
    *,
    rating: int = 3,
) -> None:
    """Thin wrapper over study_service.review_card that forwards the user."""
    await study_service.review_card(
        user_id=user.id,
        card_id=card_id,
        rating=rating,
        is_free=(user.subscription is None or user.subscription.plan == "free"),
        db=db,
        user=user,
    )


def _utc_date_str() -> str:
    """UTC date string matching the wall helper's key format for test seeding."""
    return study_service._utcnow().astimezone(timezone.utc).date().isoformat()


# ── Per-test isolation: fresh FakeRedis + event capture ─────────────────────


@pytest_asyncio.fixture(loop_scope="session")
async def fake_redis(monkeypatch):
    fr = FakeRedis()
    monkeypatch.setattr(study_service, "_get_redis", lambda: fr)
    return fr


@pytest.fixture
def captured_events(monkeypatch):
    """Capture every ``analytics_track`` call inside study_service."""
    events: list[tuple[str, str, dict]] = []

    def _capture(user_id, event, properties=None):
        events.append((str(user_id), event, dict(properties or {})))

    monkeypatch.setattr(study_service, "analytics_track", _capture)
    return events


# ── Tests ───────────────────────────────────────────────────────────────────


# BE-1 — AC-1
async def test_free_user_review_up_to_cap_succeed(db_session, fake_redis):
    """Submits 1..CAP for a free user all return successfully; counter tracks each.

    Boundary derives from settings — see LD-001 amendment 2026-04-26.
    """
    user = await _make_user(db_session, plan="free", timezone_str="UTC")
    # Need CAP distinct cards so each submit is independent
    cards = [await _make_card(db_session) for _ in range(CAP)]

    for card in cards:
        await _submit(db_session, user, card.id)

    # All CAP counted; no wall raised
    assert fake_redis.incr_calls == CAP
    key = next(iter(fake_redis.store))
    assert fake_redis.store[key] == CAP


# BE-2 — AC-2
async def test_first_review_over_cap_returns_402_with_correct_payload(
    db_session, fake_redis
):
    """The (CAP+1)th submit on the same local day raises DailyReviewLimitError
    with AC-2 payload. Boundary derives from settings."""
    user = await _make_user(db_session, plan="free", timezone_str="Asia/Kolkata")
    cards = [await _make_card(db_session) for _ in range(CAP + 1)]

    for card in cards[:CAP]:
        await _submit(db_session, user, card.id)

    # (CAP+1)th card — snapshot its card_progress state to assert no mutation
    target = cards[CAP]
    with pytest.raises(DailyReviewLimitError) as excinfo:
        await _submit(db_session, user, target.id)

    payload = excinfo.value.payload
    assert payload["error"] == "free_tier_limit"
    assert payload["trigger"] == "daily_review"
    assert payload["cards_consumed"] == CAP
    assert payload["cards_limit"] == CAP
    # resets_at is ISO 8601 with tz offset
    assert "resets_at" in payload
    resets = datetime.fromisoformat(payload["resets_at"])
    assert resets.tzinfo is not None
    # Must be in the future (next local midnight)
    assert resets > datetime.now(timezone.utc)

    # AC-2: card_progress row for the walled card must NOT exist
    cp = (
        await db_session.execute(
            select(CardProgress)
            .where(CardProgress.user_id == user.id)
            .where(CardProgress.card_id == target.id)
        )
    ).scalar_one_or_none()
    assert cp is None, "walled submit must not create a card_progress row"


# BE-3 — AC-3 + §Counter Scope Option 2
async def test_pro_user_never_hits_wall(db_session, fake_redis):
    """Pro user submits 20 reviews: no wall, no Redis INCR (Option 2)."""
    user = await _make_user(db_session, plan="pro", timezone_str="UTC")
    cards = [await _make_card(db_session) for _ in range(20)]

    for card in cards:
        await _submit(db_session, user, card.id)

    # Option 2: zero Redis interaction for Pro
    assert fake_redis.incr_calls == 0
    assert fake_redis.store == {}


# BE-4 — AC-9
async def test_admin_bypasses_wall_regardless_of_plan(db_session, fake_redis):
    """Admin + free plan still gets unlimited submits."""
    user = await _make_user(
        db_session, plan="free", role="admin", timezone_str="UTC"
    )
    cards = [await _make_card(db_session) for _ in range(20)]

    for card in cards:
        await _submit(db_session, user, card.id)

    # Admin bypass is an early-exit; Redis is not touched
    assert fake_redis.incr_calls == 0


# BE-5 — AC-4 (timezone reset, LA)
async def test_counter_resets_at_user_local_midnight_tz_la(
    db_session, fake_redis, monkeypatch
):
    """LA user: CAP submits at 15:30 local, (CAP+1)th at 16:30 same local day → 402.
    After 00:01 local next day → 200. Boundary derives from settings."""
    user = await _make_user(
        db_session, plan="free", timezone_str="America/Los_Angeles"
    )
    cards = [await _make_card(db_session) for _ in range(CAP + 2)]
    la = ZoneInfo("America/Los_Angeles")

    # Day-1 at 15:30 LA local = 23:30 UTC (LA is UTC-7 in PDT)
    t1 = datetime(2026, 6, 15, 15, 30, tzinfo=la).astimezone(timezone.utc)
    monkeypatch.setattr(study_service, "_utcnow", lambda: t1)
    for card in cards[:CAP]:
        await _submit(db_session, user, card.id)

    # Day-1 at 16:30 LA local = 00:30 UTC (next UTC day, same LA day)
    t2 = datetime(2026, 6, 15, 16, 30, tzinfo=la).astimezone(timezone.utc)
    monkeypatch.setattr(study_service, "_utcnow", lambda: t2)
    with pytest.raises(DailyReviewLimitError):
        await _submit(db_session, user, cards[CAP].id)

    # Day-2 at 00:01 LA local = 07:01 UTC next day → fresh Redis key
    t3 = datetime(2026, 6, 16, 0, 1, tzinfo=la).astimezone(timezone.utc)
    monkeypatch.setattr(study_service, "_utcnow", lambda: t3)
    await _submit(db_session, user, cards[CAP + 1].id)  # should not raise

    # Two distinct keys exist (day-1 had CAP accepted + 1 walled INCR; day-2 at 1).
    # The walled INCR still mutates the counter — the raise happens after,
    # leaving the observable store at CAP+1. What the user sees is
    # count_after=CAP in the analytics event (capped) and the raise.
    assert len(fake_redis.store) == 2
    counts = sorted(fake_redis.store.values())
    assert counts == [1, CAP + 1]


# BE-6 — AC-4 default path
async def test_counter_defaults_to_utc_when_user_has_no_timezone(
    db_session, fake_redis, monkeypatch
):
    """User with no EmailPreference row → UTC day-key."""
    user = await _make_user(db_session, plan="free")  # no timezone_str → no row
    card = await _make_card(db_session)

    t = datetime(2026, 6, 15, 23, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(study_service, "_utcnow", lambda: t)
    await _submit(db_session, user, card.id)

    expected_key = f"daily_cards:{user.id}:2026-06-15"
    assert expected_key in fake_redis.store


# BE-7 — fail-open
async def test_redis_outage_fails_open(
    db_session, captured_events, monkeypatch
):
    """``_get_redis()`` → None: 20 free-user submits all succeed; events carry counter_unavailable=true."""
    monkeypatch.setattr(study_service, "_get_redis", lambda: None)
    user = await _make_user(db_session, plan="free", timezone_str="UTC")
    cards = [await _make_card(db_session) for _ in range(20)]

    for card in cards:
        await _submit(db_session, user, card.id)  # must not raise

    submits = [e for e in captured_events if e[1] == "daily_card_submit"]
    assert len(submits) == 20
    for _uid, _name, props in submits:
        assert props["counter_unavailable"] is True
        assert props["was_walled"] is False
        assert props["plan"] == "free"


# BE-8 — concurrent submits
async def test_concurrent_submits_at_boundary_increment_atomically(
    db_session, fake_redis, monkeypatch
):
    """Two concurrent wall-checks at count=CAP-1 return post-values CAP and CAP+1.

    SQLAlchemy AsyncSession is not safe to share across concurrent
    coroutines (`InterfaceError: cannot use Connection.transaction() in
    a manually started transaction`), so we exercise the wall helper
    directly to focus the test on Redis INCR atomicity — the actual
    invariant the spec names (§Edge Cases: "Two concurrent callers see
    post-values CAP and CAP+1 respectively; the CAP-call succeeds; the
    (CAP+1)-call 402s"). Boundary derives from settings.

    FakeRedis.incr is atomic under asyncio because the GIL serialises the
    dict mutation, matching real Redis INCR semantics.
    """
    user = await _make_user(db_session, plan="free", timezone_str="UTC")
    # Pre-seed the counter to CAP-1 so the next two incrs land at CAP and CAP+1.
    key_today = f"daily_cards:{user.id}:{_utc_date_str()}"
    fake_redis.store[key_today] = CAP - 1

    raised: list[bool] = []

    async def _attempt() -> None:
        try:
            await study_service._check_daily_wall(user, db_session)
            raised.append(False)
        except DailyReviewLimitError:
            raised.append(True)

    await asyncio.gather(_attempt(), _attempt())

    assert fake_redis.store[key_today] == CAP + 1
    assert sorted(raised) == [False, True]  # exactly one wall; exactly one pass


# BE-9 — AC-8
async def test_pro_upgrade_mid_wall_bypasses_immediately(
    db_session, fake_redis
):
    """User hits 402 at the (CAP+1)th submit as free; flip subscription to pro;
    the next submit goes through; Redis untouched by the pro submit. Boundary
    derives from settings."""
    user = await _make_user(db_session, plan="free", timezone_str="UTC")
    cards = [await _make_card(db_session) for _ in range(CAP + 2)]

    for card in cards[:CAP]:
        await _submit(db_session, user, card.id)
    with pytest.raises(DailyReviewLimitError):
        await _submit(db_session, user, cards[CAP].id)

    # Simulate Stripe webhook upgrading plan
    user.subscription.plan = "pro"
    await db_session.flush()

    pre_incr = fake_redis.incr_calls
    await _submit(db_session, user, cards[CAP + 1].id)  # must not raise
    # Option 2: no Redis call for pro
    assert fake_redis.incr_calls == pre_incr


# BE-10 — AC-10 backend side
async def test_posthog_daily_card_submit_fires_with_correct_props(
    db_session, fake_redis, captured_events
):
    """One free-user submit → daily_card_submit with expected props."""
    user = await _make_user(db_session, plan="free", timezone_str="UTC")
    card = await _make_card(db_session)

    await _submit(db_session, user, card.id)

    submits = [e for e in captured_events if e[1] == "daily_card_submit"]
    assert len(submits) == 1
    uid, _name, props = submits[0]
    assert uid == user.id
    assert props == {
        "plan": "free",
        "count_after": 1,
        "was_walled": False,
        "counter_unavailable": False,
    }


# BE-11 — AC-6
async def test_walled_submit_does_not_consume_streak_freeze(
    db_session, fake_redis
):
    """Walled (CAP+1)th submit leaves GamificationStats.freezes_available +
    streak untouched.

    AC-6 asserts the *walled submit* has no gamification side-effects. The
    CAP preceding legitimate submits do tick the streak and XP (that's the
    regular review path), so we snapshot the gamification row AFTER the CAPth
    submit and assert it's byte-for-byte identical after the walled (CAP+1)th.
    Boundary derives from settings.
    """
    user = await _make_user(db_session, plan="free", timezone_str="UTC")
    stats = GamificationStats(
        user_id=user.id,
        current_streak=5,
        longest_streak=5,
        total_xp=100,
        freezes_available=3,
    )
    db_session.add(stats)
    await db_session.flush()

    cards = [await _make_card(db_session) for _ in range(CAP + 1)]
    for card in cards[:CAP]:
        await _submit(db_session, user, card.id)

    # Snapshot the gamification state between submit CAP (allowed) and the
    # walled (CAP+1)th.
    await db_session.refresh(stats)
    snapshot = {
        "current_streak": stats.current_streak,
        "longest_streak": stats.longest_streak,
        "total_xp": stats.total_xp,
        "freezes_available": stats.freezes_available,
    }

    with pytest.raises(DailyReviewLimitError):
        await _submit(db_session, user, cards[CAP].id)

    await db_session.refresh(stats)
    assert stats.freezes_available == snapshot["freezes_available"]
    assert stats.current_streak == snapshot["current_streak"]
    assert stats.longest_streak == snapshot["longest_streak"]
    assert stats.total_xp == snapshot["total_xp"]
