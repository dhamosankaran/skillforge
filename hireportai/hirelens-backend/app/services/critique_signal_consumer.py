"""Critique-score consumer — Phase 6 slice 6.13.5a.

Spec: docs/specs/phase-6/12-quality-signals.md §6.2 + §12 D-3.

Lifts the four per-dimension scores out of a ``CritiqueSchema`` payload
and writes one ``signal_source='critique'`` row per (lesson_id,
dimension) tuple. Called from ``ingestion_worker.run_ingestion_job``
between Stage 2 critique and Stage 3 persist (§12 D-3 lock = write-time
hook; decouples admin dashboard from R2 availability).

Score normalisation: ``CritiqueDimension.score`` is an int 1..5 (per
``app/schemas/ingestion.py:117``). We store ``score / 5.0`` so the
``card_quality_signals.score`` column is always in [0.20, 1.00] for
critique rows.

Idempotent — UPSERTs on the LD-J2-extended 5-tuple (with
``recorded_by_user_id IS NULL`` for critique rows so the 4-tuple
collision still applies).
"""
from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.card_quality_signal import CardQualitySignalWrite
from app.schemas.ingestion import CritiqueSchema
from app.services import card_quality_signal_service

logger = logging.getLogger(__name__)


async def persist_critique_signals(
    *,
    lesson_ids: Iterable[str],
    critique: CritiqueSchema,
    job_id: str,
    db: AsyncSession,
) -> int:
    """UPSERT one ``signal_source='critique'`` row per (lesson, dimension).

    Returns the number of rows written (lessons × dimensions). Re-running
    with the same inputs is a no-op for ``score`` but bumps
    ``recorded_at`` per §12 D-13.

    Partial-failure-skip per §4.3: if a single UPSERT fails the
    consumer logs and continues — UPSERT semantics make a follow-up
    re-run idempotent for the rows that landed.
    """
    written = 0
    ids = [lid for lid in lesson_ids if lid]
    if not ids or not critique.dimensions:
        return 0
    for lesson_id in ids:
        for dim in critique.dimensions:
            try:
                await card_quality_signal_service.upsert_signal(
                    CardQualitySignalWrite(
                        lesson_id=lesson_id,
                        quiz_item_id=None,
                        signal_source="critique",
                        dimension=dim.name,
                        score=dim.score / 5.0,
                        source_ref=job_id,
                        recorded_by_user_id=None,
                    ),
                    db,
                )
                written += 1
            except SQLAlchemyError as exc:  # pragma: no cover — defensive
                logger.warning(
                    "critique_signal_consumer: UPSERT failed for "
                    "lesson=%s dimension=%s job=%s: %s",
                    lesson_id,
                    dim.name,
                    job_id,
                    exc,
                )
    return written
