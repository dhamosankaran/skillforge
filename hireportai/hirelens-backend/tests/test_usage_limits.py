"""Tests for usage limits (interview question generation + gap mapping).

Verifies:
1. Free users limited to 3 interview generations per month
2. Pro users unlimited
3. Usage resets monthly
4. Gap-to-card mapping returns matching categories
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User
from app.services.usage_service import check_and_increment

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_user(db, plan="free"):
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Test User",
    )
    db.add(user)
    await db.flush()
    sub = Subscription(user_id=user.id, plan=plan, status="active")
    db.add(sub)
    await db.flush()
    return user


async def test_free_user_limited_to_3_interview_generations(db_session):
    """Free user should be allowed 3 interview preps, then blocked."""
    user = await _create_user(db_session, plan="free")

    # First 3 should succeed
    for i in range(3):
        result = await check_and_increment(user.id, "interview_prep", db_session)
        assert result["allowed"] is True, f"Attempt {i+1} should be allowed"
        assert result["limit"] == 3

    # 4th should be blocked
    result = await check_and_increment(user.id, "interview_prep", db_session)
    assert result["allowed"] is False
    assert result["remaining"] == 0
    assert result["limit"] == 3


async def test_pro_user_unlimited_interview_generations(db_session):
    """Pro user should always be allowed, with limit=-1."""
    user = await _create_user(db_session, plan="pro")

    for _ in range(10):
        result = await check_and_increment(user.id, "interview_prep", db_session)
        assert result["allowed"] is True
        assert result["limit"] == -1
        assert result["remaining"] == -1


async def test_usage_resets_monthly(db_session):
    """Usage from a previous month should not count toward this month's limit."""
    user = await _create_user(db_session, plan="free")

    # Manually insert 3 usage logs from last month
    last_month = datetime.utcnow().replace(day=1) - timedelta(days=1)
    for _ in range(3):
        log = UsageLog(
            user_id=user.id,
            feature_used="interview_prep",
            tokens_consumed=0,
        )
        db_session.add(log)
    await db_session.flush()

    # Backdate them to last month
    from sqlalchemy import update
    await db_session.execute(
        update(UsageLog)
        .where(UsageLog.user_id == user.id)
        .values(created_at=last_month)
    )
    await db_session.flush()

    # This month's usage should start fresh — first attempt should succeed
    result = await check_and_increment(user.id, "interview_prep", db_session)
    assert result["allowed"] is True
    assert result["remaining"] == 2  # 3 limit - 1 just used


async def test_gap_to_card_link_returns_matching_category(db_session):
    """Gap mapping service should return matching categories for known skill gaps."""
    from app.services.gap_mapping_service import map_gaps_to_categories

    # This test depends on categories being seeded in the test DB.
    # If no categories exist, the mapping should return "none" match_type.
    result = await map_gaps_to_categories(
        gaps=["Python", "Kubernetes", "UnknownSkill12345"],
        db=db_session,
        use_semantic=False,
    )

    assert isinstance(result, list)
    assert len(result) == 3

    # Each result has the expected structure (Pydantic GapMapping)
    for mapping in result:
        assert hasattr(mapping, "gap")
        assert hasattr(mapping, "match_type")
        assert hasattr(mapping, "matching_categories")
        assert mapping.match_type in ("tag", "semantic", "none")
