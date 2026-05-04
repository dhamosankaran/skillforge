"""Loop-progress aggregator service for the AppShell strip (E-051 / spec #66).

Computes per-tracker gap-card review progress + days since last scan.

Spec §6.1 / §12 D-3 / §12 D-13.

D-3: gap-card mapping = skill-name → category lookup (matches the live
`MissingSkillsPanel` precedent; spec #22). Card-tag lookup is forward
work and not implemented this slice.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.tracker import TrackerApplicationModel
from app.models.tracker_application_score import TrackerApplicationScore
from app.schemas.loop_progress import LoopProgressResponse
from app.utils.skill_taxonomy import get_skill_category


class TrackerNotFoundError(Exception):
    """Tracker application missing or not owned by the requesting user."""


def _parse_skills(raw: str | None) -> list[str]:
    """Return the JSON-encoded skills_missing list (empty on absent/invalid)."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [s for s in parsed if isinstance(s, str) and s.strip()]


async def get_loop_progress(
    db: AsyncSession,
    user_id: str,
    tracker_id: str,
) -> LoopProgressResponse:
    """Compute LoopProgressResponse for the given tracker.

    Raises TrackerNotFoundError when the tracker is missing or owned by a
    different user.
    """
    tracker_q = await db.execute(
        select(TrackerApplicationModel).where(
            TrackerApplicationModel.id == tracker_id,
            TrackerApplicationModel.user_id == user_id,
        )
    )
    tracker = tracker_q.scalar_one_or_none()
    if tracker is None:
        raise TrackerNotFoundError(tracker_id)

    skills = _parse_skills(tracker.skills_missing)
    category_names = sorted({get_skill_category(s) for s in skills})

    total_gap_cards = 0
    reviewed_gap_cards = 0
    if category_names:
        cat_rows = await db.execute(
            select(Category.id).where(Category.name.in_(category_names))
        )
        category_ids = [row[0] for row in cat_rows.all()]
        if category_ids:
            total_q = await db.execute(
                select(func.count(Card.id)).where(
                    Card.category_id.in_(category_ids),
                    Card.deleted_at.is_(None),
                )
            )
            total_gap_cards = int(total_q.scalar_one() or 0)

            reviewed_q = await db.execute(
                select(func.count(func.distinct(Card.id)))
                .join(CardProgress, CardProgress.card_id == Card.id)
                .where(
                    Card.category_id.in_(category_ids),
                    Card.deleted_at.is_(None),
                    CardProgress.user_id == user_id,
                    CardProgress.reps > 0,
                )
            )
            reviewed_gap_cards = int(reviewed_q.scalar_one() or 0)

    percent_reviewed = (
        round(reviewed_gap_cards / total_gap_cards * 100.0, 1)
        if total_gap_cards > 0
        else 0.0
    )

    last_scan_q = await db.execute(
        select(func.max(TrackerApplicationScore.scanned_at)).where(
            TrackerApplicationScore.tracker_application_id == tracker_id
        )
    )
    last_scan_at: datetime | None = last_scan_q.scalar_one_or_none()
    days_since_last_scan: int | None
    if last_scan_at is None:
        days_since_last_scan = None
    else:
        if last_scan_at.tzinfo is None:
            last_scan_at = last_scan_at.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - last_scan_at
        days_since_last_scan = max(0, delta.days)

    return LoopProgressResponse(
        tracker_application_id=tracker_id,
        total_gap_cards=total_gap_cards,
        reviewed_gap_cards=reviewed_gap_cards,
        percent_reviewed=percent_reviewed,
        days_since_last_scan=days_since_last_scan,
    )
