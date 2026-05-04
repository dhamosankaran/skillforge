"""Career-Climber role-intent service (E-052 / B-125a).

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §6.1 + §4.4.

Public functions:

- ``set_intent`` — append-only write; supersedes the prior current row
  (stamps ``superseded_at=now()``) and inserts a new current row.
- ``get_current_intent`` — returns the row with ``superseded_at IS NULL``
  for a user, or None.
- ``clear_intent`` — stamps the prior current row's ``superseded_at``
  without inserting a replacement (D-6).
- ``get_aggregate_stats`` — privacy-contract enforcement point (§4.4).
  Returns ``AggregateStats`` only when the cohort meets ``MIN_COHORT_SIZE``;
  ``None`` otherwise. The composer never bypasses; it gates rendering on
  the ``None`` return.

Implementation note (drift flag — see SESSION-STATE.md): spec §6.1 sketches
the aggregate query as ``quiz_review_events JOIN cards JOIN categories``,
but ``QuizReviewEvent`` is keyed on ``quiz_items`` (newer Phase-6 surface),
not legacy ``cards``. CC users today study via legacy FSRS cards, so this
implementation aggregates ``CardProgress.reps`` per ``Category`` as the
study-time proxy. A future spec amendment can promote to ``quiz_review_
events`` when CC users migrate to the new lessons surface.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import distinct, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.user_career_intent import UserCareerIntent
from app.schemas.career_intent import (
    AggregateStats,
    CategoryShare,
)


MIN_COHORT_SIZE = 10
TOP_CATEGORIES_K = 3


async def set_intent(
    db: AsyncSession,
    user_id: str,
    target_role: str,
    target_quarter: str,
) -> UserCareerIntent:
    """Append-only write — supersede prior current row, insert a new one.

    Caller (route handler) owns the commit boundary.
    """
    now = datetime.now(timezone.utc)

    await db.execute(
        update(UserCareerIntent)
        .where(UserCareerIntent.user_id == user_id)
        .where(UserCareerIntent.superseded_at.is_(None))
        .values(superseded_at=now)
    )

    intent = UserCareerIntent(
        user_id=user_id,
        target_role=target_role,
        target_quarter=target_quarter,
    )
    db.add(intent)
    await db.flush()
    await db.refresh(intent)
    return intent


async def get_current_intent(
    db: AsyncSession, user_id: str
) -> Optional[UserCareerIntent]:
    """Return the row with ``superseded_at IS NULL`` (at most one)."""
    result = await db.execute(
        select(UserCareerIntent)
        .where(UserCareerIntent.user_id == user_id)
        .where(UserCareerIntent.superseded_at.is_(None))
    )
    return result.scalar_one_or_none()


async def clear_intent(db: AsyncSession, user_id: str) -> bool:
    """Stamp the prior current row; do NOT insert a replacement (D-6).

    Returns True when a row was cleared, False when there was no current
    intent to clear (no-op).
    """
    result = await db.execute(
        update(UserCareerIntent)
        .where(UserCareerIntent.user_id == user_id)
        .where(UserCareerIntent.superseded_at.is_(None))
        .values(superseded_at=datetime.now(timezone.utc))
    )
    return (result.rowcount or 0) > 0


async def get_aggregate_stats(
    db: AsyncSession, target_role: str, target_quarter: str
) -> Optional[AggregateStats]:
    """Aggregate study-time-by-category for a ``(role, quarter)`` cohort.

    Returns ``None`` when the cohort has fewer than ``MIN_COHORT_SIZE``
    distinct users with a current intent in the bucket. This is the
    single privacy-contract enforcement point per §4.4 — the composer
    NEVER bypasses; it receives ``AggregateStats | None`` and gates
    rendering on ``is None``.
    """
    cohort_users_stmt = (
        select(UserCareerIntent.user_id)
        .where(UserCareerIntent.target_role == target_role)
        .where(UserCareerIntent.target_quarter == target_quarter)
        .where(UserCareerIntent.superseded_at.is_(None))
    )

    cohort_size_result = await db.execute(
        select(func.count(distinct(UserCareerIntent.user_id)))
        .where(UserCareerIntent.target_role == target_role)
        .where(UserCareerIntent.target_quarter == target_quarter)
        .where(UserCareerIntent.superseded_at.is_(None))
    )
    cohort_size = int(cohort_size_result.scalar_one() or 0)

    if cohort_size < MIN_COHORT_SIZE:
        return None

    total_reps_result = await db.execute(
        select(func.coalesce(func.sum(CardProgress.reps), 0))
        .where(CardProgress.user_id.in_(cohort_users_stmt))
    )
    total_reps = int(total_reps_result.scalar_one() or 0)
    if total_reps == 0:
        return None

    top_rows = (
        await db.execute(
            select(
                Category.name.label("category_name"),
                func.coalesce(
                    func.sum(CardProgress.reps), 0
                ).label("cat_reps"),
            )
            .select_from(CardProgress)
            .join(Card, Card.id == CardProgress.card_id)
            .join(Category, Category.id == Card.category_id)
            .where(CardProgress.user_id.in_(cohort_users_stmt))
            .group_by(Category.name)
            .order_by(func.sum(CardProgress.reps).desc())
            .limit(TOP_CATEGORIES_K)
        )
    ).all()

    top_categories = [
        CategoryShare(
            category_name=row.category_name,
            percent_of_study_time=round(
                100.0 * (int(row.cat_reps) / total_reps), 1
            ),
        )
        for row in top_rows
    ]

    return AggregateStats(
        target_role=target_role,
        target_quarter=target_quarter,
        cohort_size=cohort_size,
        top_categories=top_categories,
    )


__all__ = [
    "MIN_COHORT_SIZE",
    "TOP_CATEGORIES_K",
    "clear_intent",
    "get_aggregate_stats",
    "get_current_intent",
    "set_intent",
]
