"""Card-quality-signal UPSERT helper + per-source readers.

Phase 6 slice 6.13.5a — implements §6.1 of
``docs/specs/phase-6/12-quality-signals.md``.

This is the only service that writes to ``card_quality_signals``.
Writers (``critique_signal_consumer``, ``admin_content_quality_service``
extension, future ``thumbs_service``) call ``upsert_signal``; readers
call ``get_signals_for_lesson`` or ``get_critique_scores_for_lessons``
for batch-friendly admin dashboard joins.

UPSERT semantics per §12 D-8: ``INSERT ... ON CONFLICT (...) DO UPDATE
SET score=EXCLUDED.score, recorded_at=NOW()``. Caller owns the
transaction (``db.flush``, not ``db.commit``) — mirrors slice 6.0
``analytics_event_service`` write-only pattern.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_quality_signal import CardQualitySignal
from app.schemas.card_quality_signal import (
    CardQualitySignalRow,
    CardQualitySignalWrite,
)

logger = logging.getLogger(__name__)


# Critique dimensions per spec #10 §5.5 ``CritiqueDimension.name`` enum.
CRITIQUE_DIMENSIONS = ("accuracy", "clarity", "completeness", "cohesion")


async def upsert_signal(
    payload: CardQualitySignalWrite,
    db: AsyncSession,
) -> CardQualitySignal:
    """Idempotent UPSERT into ``card_quality_signals``.

    Returns the persisted ORM row (read-after-write so the row identity
    is the post-conflict-resolution row, not whatever placeholder ORM
    hydrates from the candidate values). Caller is responsible for
    transaction management — this helper calls ``db.flush`` but not
    ``db.commit``, so it composes inside the existing admin-dashboard /
    worker / request transactions.
    """
    score = Decimal(f"{payload.score:.2f}")
    stmt = (
        pg_insert(CardQualitySignal)
        .values(
            lesson_id=payload.lesson_id,
            quiz_item_id=payload.quiz_item_id,
            signal_source=payload.signal_source,
            dimension=payload.dimension,
            score=score,
            source_ref=payload.source_ref,
            recorded_by_user_id=payload.recorded_by_user_id,
        )
        .on_conflict_do_update(
            constraint="ux_card_quality_signals_key",
            set_={
                "score": score,
                "source_ref": payload.source_ref,
                "recorded_at": func.now(),
            },
        )
    )
    await db.execute(stmt)
    await db.flush()

    # Read-after-write — the UNIQUE 5-tuple addresses exactly one row.
    # ``execution_options(populate_existing=True)`` so any prior
    # identity-mapped instance is refreshed with the post-UPSERT state
    # rather than served stale from the session cache.
    fetch = select(CardQualitySignal).where(
        CardQualitySignal.lesson_id == payload.lesson_id,
        CardQualitySignal.signal_source == payload.signal_source,
        CardQualitySignal.dimension == payload.dimension,
    )
    if payload.quiz_item_id is None:
        fetch = fetch.where(CardQualitySignal.quiz_item_id.is_(None))
    else:
        fetch = fetch.where(
            CardQualitySignal.quiz_item_id == payload.quiz_item_id
        )
    if payload.recorded_by_user_id is None:
        fetch = fetch.where(CardQualitySignal.recorded_by_user_id.is_(None))
    else:
        fetch = fetch.where(
            CardQualitySignal.recorded_by_user_id == payload.recorded_by_user_id
        )
    return (
        await db.execute(fetch.execution_options(populate_existing=True))
    ).scalar_one()


async def get_signals_for_lesson(
    lesson_id: str,
    db: AsyncSession,
    *,
    signal_source: Optional[str] = None,
) -> list[CardQualitySignalRow]:
    """All signals for a single lesson, optionally filtered by source."""
    stmt = select(CardQualitySignal).where(
        CardQualitySignal.lesson_id == lesson_id
    )
    if signal_source is not None:
        stmt = stmt.where(CardQualitySignal.signal_source == signal_source)
    rows = (await db.execute(stmt)).scalars().all()
    return [CardQualitySignalRow.model_validate(r) for r in rows]


async def get_critique_scores_for_lessons(
    lesson_ids: Iterable[str],
    db: AsyncSession,
) -> dict[str, dict[str, float]]:
    """Per-lesson critique scores keyed by lesson_id → {dimension: score}.

    Only ``signal_source='critique'`` rows are returned, and only for
    rows with ``quiz_item_id IS NULL`` (lesson-level critique signals;
    per-quiz_item critique is not part of v1 per §12 D-3 + spec §4.2.1).

    Returns an empty dict when no rows match — admin dashboard treats a
    missing lesson_id as "no critique signal yet" (renders ``None``).
    """
    ids = [lid for lid in lesson_ids if lid]
    if not ids:
        return {}
    stmt = select(CardQualitySignal).where(
        CardQualitySignal.lesson_id.in_(ids),
        CardQualitySignal.signal_source == "critique",
        CardQualitySignal.quiz_item_id.is_(None),
    )
    out: dict[str, dict[str, float]] = defaultdict(dict)
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        out[row.lesson_id][row.dimension] = float(row.score)
    return dict(out)


async def get_persisted_user_review_scores_for_quiz_items(
    quiz_item_ids: Iterable[str],
    db: AsyncSession,
) -> dict[str, float]:
    """Per-quiz_item ``user_review`` ``pass_rate`` score on disk.

    Used by the admin dashboard to surface what was actually persisted
    for each quiz_item (mirrors ``LessonQualityRow.persisted_quality_score``
    on the lesson side).
    """
    ids = [qid for qid in quiz_item_ids if qid]
    if not ids:
        return {}
    stmt = select(CardQualitySignal).where(
        CardQualitySignal.quiz_item_id.in_(ids),
        CardQualitySignal.signal_source == "user_review",
        CardQualitySignal.dimension == "pass_rate",
        CardQualitySignal.recorded_by_user_id.is_(None),
    )
    out: dict[str, float] = {}
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        out[row.quiz_item_id] = float(row.score)
    return out


# ── Slice 6.13.5b — thumbs aggregate readers (§6.1) ──────────────────────────


async def get_thumbs_aggregate(
    lesson_id: str,
    db: AsyncSession,
    *,
    quiz_item_id: Optional[str] = None,
) -> tuple[Optional[float], int]:
    """Mean user-thumbs score + count for ``(lesson_id, quiz_item_id)``.

    Aggregates only ``signal_source='user_thumbs'`` rows where
    ``dimension='helpful'``. Returns ``(None, 0)`` when no thumbs
    rows exist (mirrors the cold-start contract on the FE).
    """
    stmt = select(CardQualitySignal.score).where(
        CardQualitySignal.lesson_id == lesson_id,
        CardQualitySignal.signal_source == "user_thumbs",
        CardQualitySignal.dimension == "helpful",
    )
    if quiz_item_id is None:
        stmt = stmt.where(CardQualitySignal.quiz_item_id.is_(None))
    else:
        stmt = stmt.where(CardQualitySignal.quiz_item_id == quiz_item_id)
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return None, 0
    floats = [float(r) for r in rows]
    return sum(floats) / len(floats), len(floats)


async def get_thumbs_aggregates_by_lesson(
    lesson_ids: Iterable[str],
    db: AsyncSession,
) -> dict[str, tuple[float, int]]:
    """Batch helper — per-lesson thumbs aggregate keyed by lesson_id.

    Used by the admin dashboard to populate
    ``LessonQualityRow.thumbs_aggregate`` + ``thumbs_count`` without
    N+1 round-trips. Lesson-level rows only (``quiz_item_id IS NULL``).
    """
    ids = [lid for lid in lesson_ids if lid]
    if not ids:
        return {}
    stmt = select(
        CardQualitySignal.lesson_id, CardQualitySignal.score
    ).where(
        CardQualitySignal.lesson_id.in_(ids),
        CardQualitySignal.signal_source == "user_thumbs",
        CardQualitySignal.dimension == "helpful",
        CardQualitySignal.quiz_item_id.is_(None),
    )
    grouped: dict[str, list[float]] = {}
    for lesson_id, score in (await db.execute(stmt)).all():
        grouped.setdefault(lesson_id, []).append(float(score))
    return {
        lid: (sum(scores) / len(scores), len(scores))
        for lid, scores in grouped.items()
    }


async def get_user_thumbs_for_lesson(
    *,
    user_id: str,
    lesson_id: str,
    db: AsyncSession,
) -> Optional[CardQualitySignal]:
    """The given user's thumbs row for ``lesson_id`` (lesson-level only).

    Returns ``None`` when the user has not submitted thumbs. Used by
    ``lesson_service.get_lesson_with_quizzes`` to seed
    ``LessonWithQuizzesResponse.viewer_thumbs`` per §12 D-12.
    """
    stmt = select(CardQualitySignal).where(
        CardQualitySignal.lesson_id == lesson_id,
        CardQualitySignal.recorded_by_user_id == user_id,
        CardQualitySignal.signal_source == "user_thumbs",
        CardQualitySignal.dimension == "helpful",
        CardQualitySignal.quiz_item_id.is_(None),
    )
    return (await db.execute(stmt)).scalar_one_or_none()
