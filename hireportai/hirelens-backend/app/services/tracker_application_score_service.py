"""Score history reads/writes for the ATS re-scan loop (E-043 / spec #63).

Append-only event-shape table per §4.4 of the spec — no UPDATE/DELETE
from application code; rows cascade with their owning tracker row /
user. Public surface mirrors §6.3 of the spec:

- ``write_score_row`` — INSERT one history row.
- ``find_by_dedupe`` — §12 D-2 short-circuit lookup.
- ``get_score_history`` — chronological (oldest-first), tenant-scoped.
- ``compute_delta`` — pure helper; ``None`` when ``len(history) < 2``.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.response_models import AnalysisResponse
from app.models.tracker import TrackerApplicationModel
from app.models.tracker_application_score import TrackerApplicationScore
from app.schemas.rescan import ScoreDelta, ScoreHistoryEntry


def _require_user_id(user_id: str) -> None:
    if user_id is None:
        raise ValueError(
            "user_id is required; tracker_application_score_service is "
            "tenant-scoped"
        )


async def write_score_row(
    *,
    tracker_application_id: str,
    user_id: str,
    response: AnalysisResponse,
    scan_id: Optional[str],
    jd_hash: str,
    resume_hash: str,
    db: AsyncSession,
) -> TrackerApplicationScore:
    """INSERT one ``tracker_application_scores`` row.

    Field-name mapping mirrors JC #1 disk-truth: per-axis floats from
    ``response.score_breakdown`` (``keyword_match`` / ``skills_coverage``
    / ``formatting_compliance`` / ``bullet_strength``) land on the
    ``*_score`` columns; ``response.ats_score`` (int) lands on
    ``overall_score``.
    """
    _require_user_id(user_id)
    breakdown = response.score_breakdown
    row = TrackerApplicationScore(
        tracker_application_id=tracker_application_id,
        user_id=user_id,
        scan_id=scan_id,
        overall_score=response.ats_score,
        keyword_match_score=float(breakdown.keyword_match),
        skills_coverage_score=float(breakdown.skills_coverage),
        formatting_compliance_score=float(breakdown.formatting_compliance),
        bullet_strength_score=float(breakdown.bullet_strength),
        jd_hash=jd_hash,
        resume_hash=resume_hash,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def find_by_dedupe(
    *,
    tracker_application_id: str,
    jd_hash: str,
    resume_hash: str,
    db: AsyncSession,
) -> Optional[TrackerApplicationScore]:
    """§12 D-2 short-circuit lookup.

    Returns the most-recent matching row when the same
    ``(jd_hash, resume_hash)`` pair has already been scored against this
    tracker application. None otherwise.
    """
    stmt = (
        select(TrackerApplicationScore)
        .where(
            TrackerApplicationScore.tracker_application_id
            == tracker_application_id
        )
        .where(TrackerApplicationScore.jd_hash == jd_hash)
        .where(TrackerApplicationScore.resume_hash == resume_hash)
        .order_by(TrackerApplicationScore.scanned_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_score_history(
    *,
    tracker_application_id: str,
    user_id: str,
    db: AsyncSession,
) -> List[TrackerApplicationScore]:
    """Return every history row for the tracker, oldest-first.

    Tenant-scoped by ``user_id`` — a non-owner request returns an empty
    list. The route layer is expected to translate "row not found / not
    owned" to 404 before reaching this service via the tracker ORM read.
    """
    _require_user_id(user_id)
    stmt = (
        select(TrackerApplicationScore)
        .where(
            TrackerApplicationScore.tracker_application_id
            == tracker_application_id
        )
        .where(TrackerApplicationScore.user_id == user_id)
        .order_by(TrackerApplicationScore.scanned_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def compute_delta(
    history: List[TrackerApplicationScore],
) -> Optional[ScoreDelta]:
    """Pre-compute the delta between the latest two rows.

    ``history`` is oldest-first per ``get_score_history``. Returns None
    when fewer than two rows exist (cold-start / first scan baseline).
    """
    if len(history) < 2:
        return None
    prev = history[-2]
    latest = history[-1]
    days_between = max(0, (latest.scanned_at - prev.scanned_at).days)
    return ScoreDelta(
        overall_delta=latest.overall_score - prev.overall_score,
        keyword_match_delta=(
            latest.keyword_match_score - prev.keyword_match_score
        ),
        skills_coverage_delta=(
            latest.skills_coverage_score - prev.skills_coverage_score
        ),
        formatting_compliance_delta=(
            latest.formatting_compliance_score - prev.formatting_compliance_score
        ),
        bullet_strength_delta=(
            latest.bullet_strength_score - prev.bullet_strength_score
        ),
        days_between=days_between,
    )


def to_history_entry(row: TrackerApplicationScore) -> ScoreHistoryEntry:
    """Flatten an ORM row to the wire shape."""
    return ScoreHistoryEntry(
        id=row.id,
        scan_id=row.scan_id,
        overall_score=row.overall_score,
        keyword_match_score=row.keyword_match_score,
        skills_coverage_score=row.skills_coverage_score,
        formatting_compliance_score=row.formatting_compliance_score,
        bullet_strength_score=row.bullet_strength_score,
        scanned_at=row.scanned_at,
    )


async def get_prior_overall_score(
    *,
    tracker_application_id: str,
    before: datetime,
    db: AsyncSession,
) -> Optional[int]:
    """Return the overall_score of the row strictly before `before`.

    Used by the /rescan handler to thread `ats_score_before` into the
    `rescan_completed` event payload (§9 / §12 D-12). None when no prior
    row exists (first scan baseline).
    """
    stmt = (
        select(TrackerApplicationScore.overall_score)
        .where(
            TrackerApplicationScore.tracker_application_id
            == tracker_application_id
        )
        .where(TrackerApplicationScore.scanned_at < before)
        .order_by(TrackerApplicationScore.scanned_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


__all__ = [
    "write_score_row",
    "find_by_dedupe",
    "get_score_history",
    "compute_delta",
    "to_history_entry",
    "get_prior_overall_score",
]


# Re-exported here so the route handler can transactionally update the
# tracker row's `ats_score` after writing a new score row.
async def update_tracker_ats_score(
    *,
    tracker: TrackerApplicationModel,
    new_score: int,
) -> None:
    """Flip the tracker row's `ats_score` to the latest value.

    The tracker row is the "current snapshot" — history lives in
    ``tracker_application_scores``. Spec §4.2 step 8: latest score wins;
    `scan_id` does NOT update (the original scan stays the canonical
    "first scan" anchor for spec #59 rehydration).
    """
    tracker.ats_score = new_score
