"""Verify the three free-tier paywall caps are env-tunable via Settings.

Each test patches the corresponding `settings.free_*_limit` field at runtime
and exercises the same enforcement path that production uses, asserting
the cap surfaces in the payload / response. Defaults match production —
the wiring is a testing affordance to flip a paywall in seconds without
seeding usage rows by hand.

Covers:
  * `free_daily_review_limit` → `study_service._check_daily_wall`
  * `free_lifetime_scan_limit` → `usage_service.check_and_increment`
                                  (feature='analyze', window='lifetime')
  * `free_monthly_interview_limit` → `usage_service.check_and_increment`
                                      (feature='interview_prep', window='monthly')
"""
from __future__ import annotations

import uuid
from typing import Optional

import pytest
import pytest_asyncio

from app.core.config import get_settings
from app.models.subscription import Subscription
from app.models.user import User
from app.services import study_service
from app.services.study_service import DailyReviewLimitError
from app.services.usage_service import check_and_increment

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── FakeRedis (mirrors test_wall.py) ───────────────────────────────────────


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key: str, ttl_seconds: int) -> None:
        pass

    def get(self, key: str) -> Optional[str]:
        val = self.store.get(key)
        return str(val) if val is not None else None

    def ping(self) -> bool:
        return True


@pytest_asyncio.fixture(loop_scope="session")
async def fake_redis(monkeypatch):
    fr = _FakeRedis()
    monkeypatch.setattr(study_service, "_get_redis", lambda: fr)
    return fr


async def _make_free_user(db) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@cap-test.com",
        name="Cap Test",
        role="user",
    )
    db.add(user)
    await db.flush()
    db.add(Subscription(user_id=user.id, plan="free", status="active"))
    await db.flush()
    await db.refresh(user, attribute_names=["subscription"])
    return user


# ── Env override flows through ──────────────────────────────────────────────


async def test_daily_review_limit_respects_env_override(
    db_session, fake_redis, monkeypatch
):
    """Patch `free_daily_review_limit = 2`: 1st + 2nd submit succeed, 3rd
    raises `DailyReviewLimitError` with `cards_limit == 2` in payload."""
    s = get_settings()
    monkeypatch.setattr(s, "free_daily_review_limit", 2)
    user = await _make_free_user(db_session)

    # 1st + 2nd succeed (count_after == 1, then 2 — both <= cap of 2).
    await study_service._check_daily_wall(user, db_session)
    await study_service._check_daily_wall(user, db_session)

    # 3rd post-increments to 3 → wall raises.
    with pytest.raises(DailyReviewLimitError) as excinfo:
        await study_service._check_daily_wall(user, db_session)

    payload = excinfo.value.payload
    assert payload["error"] == "free_tier_limit"
    assert payload["trigger"] == "daily_review"
    assert payload["cards_limit"] == 2
    assert payload["cards_consumed"] == 2


async def test_lifetime_scan_limit_respects_env_override(
    db_session, monkeypatch
):
    """Patch `free_lifetime_scan_limit = 0`: first analyze attempt walls
    immediately with `limit == 0`."""
    s = get_settings()
    monkeypatch.setattr(s, "free_lifetime_scan_limit", 0)
    user = await _make_free_user(db_session)

    result = await check_and_increment(
        user.id, "analyze", db_session, window="lifetime"
    )
    assert result["allowed"] is False
    assert result["limit"] == 0
    assert result["remaining"] == 0
    assert result["plan"] == "free"


async def test_monthly_interview_limit_respects_env_override(
    db_session, monkeypatch
):
    """Patch `free_monthly_interview_limit = 0`: first interview_prep
    attempt walls immediately with `limit == 0`."""
    s = get_settings()
    monkeypatch.setattr(s, "free_monthly_interview_limit", 0)
    user = await _make_free_user(db_session)

    result = await check_and_increment(
        user.id, "interview_prep", db_session, window="monthly"
    )
    assert result["allowed"] is False
    assert result["limit"] == 0
    assert result["remaining"] == 0
    assert result["plan"] == "free"
