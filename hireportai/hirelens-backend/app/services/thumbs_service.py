"""User-thumbs ingestion service — Phase 6 slice 6.13.5b.

Spec: docs/specs/phase-6/12-quality-signals.md §6.3 + §12 D-7 + D-9 +
D-10 + D-11.

Lesson-level only v1 per §12 D-7. Re-submitting overwrites via
``card_quality_signal_service.upsert_signal`` on the 5-tuple UNIQUE
(per §12 D-5 — ``recorded_by_user_id`` distinguishes per-user rows).
``recorded_at`` bumps on every UPSERT per §12 D-13.

Visibility — re-uses the slice 6.5 read-time invariants by going
through ``lesson_service.get_lesson_with_quizzes`` which already
applies persona / archive / publish / tier filters and raises 404 /
403. No duplicate filtering here.
"""
from __future__ import annotations

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.card_quality_signal import (
    CardQualitySignalWrite,
    ThumbsResponse,
)
from app.services import card_quality_signal_service, lesson_service
from app.services.quiz_item_study_service import QuizItemForbiddenError


class LessonNotVisibleError(Exception):
    """Raised when the lesson is missing / archived / persona-narrowed.

    Routed to HTTP 404 so we never disclose tier or persona narrowing
    via a different status (mirrors slice 6.5 invariants).
    """


async def submit_thumbs(
    *,
    lesson_id: str,
    score: Literal[-1, 1],
    user: User,
    db: AsyncSession,
) -> ThumbsResponse:
    """Persist the user's thumbs vote and return the response payload.

    Steps per §6.3:
    1. Verify the lesson is visible to the user (re-uses slice 6.5
       read-time invariants via ``lesson_service.get_lesson_with_quizzes``).
       Raises ``LessonNotVisibleError`` (route → 404) on miss /
       archive / publish / persona narrow; re-raises
       ``QuizItemForbiddenError`` (route → 403) on premium-tier
       gating.
    2. UPSERT a ``signal_source='user_thumbs'`` row.
    3. Compute lesson-level aggregate (mean + count across all users).
    4. Return ``ThumbsResponse``.
    """
    # The lesson-detail bundle re-uses slice 6.5's filters; we only
    # need the existence + visibility check, so we discard the bundle.
    bundle = await lesson_service.get_lesson_with_quizzes(
        lesson_id, db, user=user
    )
    if bundle is None:
        raise LessonNotVisibleError(lesson_id)

    await card_quality_signal_service.upsert_signal(
        CardQualitySignalWrite(
            lesson_id=lesson_id,
            quiz_item_id=None,
            signal_source="user_thumbs",
            dimension="helpful",
            score=float(score),
            source_ref=None,
            recorded_by_user_id=user.id,
        ),
        db,
    )

    aggregate, count = await card_quality_signal_service.get_thumbs_aggregate(
        lesson_id, db, quiz_item_id=None
    )
    return ThumbsResponse(
        accepted=True,
        score=score,
        aggregate_score=aggregate,
        aggregate_count=count,
    )


__all__ = ["LessonNotVisibleError", "submit_thumbs"]
