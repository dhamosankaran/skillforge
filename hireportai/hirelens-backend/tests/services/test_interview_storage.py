"""Tests for interview question storage + cache (spec #49).

Covers acceptance criteria AC-1 through AC-5b. All tests mock the LLM call
so they stay in the non-integration CI lane.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.models.interview_question_set import InterviewQuestionSet
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.responses import InterviewPrepResponse, InterviewQuestion
from app.services.interview_storage_service import generate_or_get_interview_set
from app.utils.text_hash import hash_jd

pytestmark = pytest.mark.asyncio(loop_scope="session")


JD = (
    "Senior Python engineer. Must know FastAPI, async I/O, PostgreSQL and "
    "distributed systems. Build scalable backends for large-scale products."
)
RESUME = (
    "Experienced backend engineer. Built Python services on FastAPI and "
    "PostgreSQL for five years. Owned distributed job queues at scale."
)


def _fake_response(tag: str = "a") -> InterviewPrepResponse:
    return InterviewPrepResponse(
        questions=[
            InterviewQuestion(
                question=f"Describe your FastAPI experience ({tag}).",
                star_framework=f"S:{tag} | T:{tag} | A:{tag} | R:{tag}",
            )
        ]
    )


async def _create_user(db, plan: str = "free") -> User:
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


async def _usage_count(db, user_id: str) -> int:
    result = await db.execute(
        select(func.count(UsageLog.id))
        .where(UsageLog.user_id == user_id)
        .where(UsageLog.feature_used == "interview_prep")
    )
    return int(result.scalar() or 0)


async def test_second_call_returns_cached(db_session):
    """AC-1: second call with same JD returns cached, LLM not invoked twice."""
    user = await _create_user(db_session)

    with patch(
        "app.services.gpt_service.generate_interview_questions",
        return_value=_fake_response("first"),
    ) as mock_llm:
        first = await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=False,
            db=db_session,
        )
        second = await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=False,
            db=db_session,
        )

    assert first.cached is False
    assert second.cached is True
    assert mock_llm.call_count == 1
    assert [q.question for q in second.questions] == [q.question for q in first.questions]


async def test_force_regenerate_bypasses_cache(db_session):
    """AC-2: force_regenerate=True calls LLM again and overwrites the stored row."""
    user = await _create_user(db_session)

    with patch(
        "app.services.gpt_service.generate_interview_questions",
        side_effect=[_fake_response("first"), _fake_response("second")],
    ) as mock_llm:
        first = await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=False,
            db=db_session,
        )
        regen = await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=True,
            db=db_session,
        )

    assert first.cached is False
    assert regen.cached is False
    assert mock_llm.call_count == 2
    assert regen.questions[0].question != first.questions[0].question

    # Overwrite semantics — a single row persists, holding the regenerated set.
    result = await db_session.execute(
        select(func.count(InterviewQuestionSet.id)).where(
            InterviewQuestionSet.user_id == user.id
        )
    )
    assert result.scalar_one() == 1

    row_result = await db_session.execute(
        select(InterviewQuestionSet).where(InterviewQuestionSet.user_id == user.id)
    )
    row = row_result.scalar_one()
    assert row.questions[0]["question"] == regen.questions[0].question


async def test_different_users_get_separate_sets(db_session):
    """AC-3: two users with the same JD each get their own cached row — no cross-tenant leak."""
    alice = await _create_user(db_session)
    bob = await _create_user(db_session)

    with patch(
        "app.services.gpt_service.generate_interview_questions",
        side_effect=[_fake_response("alice"), _fake_response("bob")],
    ) as mock_llm:
        alice_result = await generate_or_get_interview_set(
            user_id=alice.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=False,
            db=db_session,
        )
        bob_result = await generate_or_get_interview_set(
            user_id=bob.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=False,
            db=db_session,
        )

    assert alice_result.cached is False
    assert bob_result.cached is False
    assert mock_llm.call_count == 2
    assert alice_result.questions[0].question != bob_result.questions[0].question

    result = await db_session.execute(
        select(func.count(InterviewQuestionSet.id)).where(
            InterviewQuestionSet.user_id.in_([alice.id, bob.id])
        )
    )
    assert result.scalar_one() == 2


async def test_whitespace_normalization_hits_cache(db_session):
    """AC-4: whitespace / case variants produce the same jd_hash and hit the cache."""
    user = await _create_user(db_session)

    jd_noisy = f"\n\t  {JD.upper()}  \n\n  "
    assert hash_jd(JD) == hash_jd(jd_noisy), "normalization broken — hash drifted"

    with patch(
        "app.services.gpt_service.generate_interview_questions",
        return_value=_fake_response("only-once"),
    ) as mock_llm:
        first = await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=False,
            db=db_session,
        )
        second = await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=jd_noisy,
            force_regenerate=False,
            db=db_session,
        )

    assert first.cached is False
    assert second.cached is True
    assert mock_llm.call_count == 1


async def test_cached_hit_does_not_decrement_free_tier(db_session):
    """AC-5a: cache hits write no usage_logs row — free-tier counter is untouched."""
    user = await _create_user(db_session, plan="free")

    with patch(
        "app.services.gpt_service.generate_interview_questions",
        return_value=_fake_response("x"),
    ):
        await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=False,
            db=db_session,
        )
        assert await _usage_count(db_session, user.id) == 1

        for _ in range(5):
            hit = await generate_or_get_interview_set(
                user_id=user.id,
                resume_text=RESUME,
                job_description=JD,
                force_regenerate=False,
                db=db_session,
            )
            assert hit.cached is True

    assert await _usage_count(db_session, user.id) == 1


async def test_new_generation_decrements_free_tier(db_session):
    """AC-5b: each cache miss or forced regen writes exactly one usage_logs row."""
    user = await _create_user(db_session, plan="free")

    with patch(
        "app.services.gpt_service.generate_interview_questions",
        side_effect=[_fake_response(f"gen-{i}") for i in range(3)],
    ):
        # Miss #1 — new JD, counter 0 → 1.
        await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=False,
            db=db_session,
        )
        assert await _usage_count(db_session, user.id) == 1

        # Miss #2 — a different JD, counter 1 → 2.
        other_jd = JD.replace("Python", "Go")
        await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=other_jd,
            force_regenerate=False,
            db=db_session,
        )
        assert await _usage_count(db_session, user.id) == 2

        # Forced regen on the first JD, counter 2 → 3.
        await generate_or_get_interview_set(
            user_id=user.id,
            resume_text=RESUME,
            job_description=JD,
            force_regenerate=True,
            db=db_session,
        )
        assert await _usage_count(db_session, user.id) == 3
