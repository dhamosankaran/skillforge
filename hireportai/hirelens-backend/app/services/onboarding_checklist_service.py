"""Interview-Prepper onboarding checklist (Spec #41).

Pure telemetry-derived state — no new schema. Each of the five steps
checks for the existence of a row in a table already written by the
feature that step represents:

- Step 1 "scan_resume"  → `tracker_applications_v2.scan_id IS NOT NULL`
- Step 2 "review_gaps"  → transitive with step 3 (see spec §3.1)
- Step 3 "pick_category" → any `card_progress` row
- Step 4 "set_mission"   → any `missions` row (any status)
- Step 5 "first_review"  → `card_progress.reps >= 1`

Queries are cheap existence/aggregate checks; the endpoint is uncached.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_progress import CardProgress
from app.models.mission import Mission
from app.models.tracker import TrackerApplicationModel
from app.models.user import User

# Fixed step order — the frontend and tests rely on this ordering.
STEP_DEFS: tuple[dict[str, str], ...] = (
    {
        "id": "scan_resume",
        "title": "Scan your resume",
        "description": "Get your ATS score and skill gaps.",
        "link_target": "/prep/analyze",
    },
    {
        "id": "review_gaps",
        "title": "Review your gaps",
        "description": "See which skills to focus on.",
        "link_target": "/prep/results",
    },
    {
        "id": "pick_category",
        "title": "Pick a study category",
        "description": "Start with the gap that matters most.",
        "link_target": "/learn",
    },
    {
        "id": "set_mission",
        "title": "Set a mission",
        "description": "Commit to a date-bound study sprint.",
        "link_target": "/learn/mission",
    },
    {
        "id": "first_review",
        "title": "Do your first daily review",
        "description": "The habit that compounds.",
        "link_target": "/learn/daily",
    },
)


class WrongPersonaError(Exception):
    """Raised when a non-Interview-Prepper user requests the checklist."""


@dataclass(frozen=True)
class _StepSignals:
    """Intermediate result of the telemetry queries."""

    scan_at: Optional[datetime]
    first_card_progress_at: Optional[datetime]
    mission_at: Optional[datetime]
    first_review_at: Optional[datetime]


async def _collect_signals(user_id: str, db: AsyncSession) -> _StepSignals:
    """Run the four telemetry queries and return the raw timestamps."""
    scan_at = (
        await db.execute(
            select(func.min(TrackerApplicationModel.created_at)).where(
                TrackerApplicationModel.user_id == user_id,
                TrackerApplicationModel.scan_id.is_not(None),
            )
        )
    ).scalar_one_or_none()

    first_card_progress_at = (
        await db.execute(
            select(func.min(CardProgress.created_at)).where(
                CardProgress.user_id == user_id
            )
        )
    ).scalar_one_or_none()

    mission_at = (
        await db.execute(
            select(func.min(Mission.created_at)).where(Mission.user_id == user_id)
        )
    ).scalar_one_or_none()

    first_review_at = (
        await db.execute(
            select(func.min(CardProgress.last_reviewed)).where(
                CardProgress.user_id == user_id,
                CardProgress.reps >= 1,
            )
        )
    ).scalar_one_or_none()

    return _StepSignals(
        scan_at=scan_at,
        first_card_progress_at=first_card_progress_at,
        mission_at=mission_at,
        first_review_at=first_review_at,
    )


async def get_checklist(user: User, db: AsyncSession) -> dict:
    """Build the checklist response for an Interview-Prepper user.

    Raises:
        WrongPersonaError — user's persona is not ``interview_prepper``.
    """
    if user.persona != "interview_prepper":
        raise WrongPersonaError(user.persona or "null")

    sig = await _collect_signals(user.id, db)

    # Step 3 completion determines step 2 (transitive — see spec §3.1).
    step_complete = {
        "scan_resume": sig.scan_at is not None,
        "pick_category": sig.first_card_progress_at is not None,
        "review_gaps": sig.first_card_progress_at is not None,
        "set_mission": sig.mission_at is not None,
        "first_review": sig.first_review_at is not None,
    }

    steps = [
        {
            "id": definition["id"],
            "title": definition["title"],
            "description": definition["description"],
            "link_target": definition["link_target"],
            "complete": step_complete[definition["id"]],
        }
        for definition in STEP_DEFS
    ]

    all_complete = all(s["complete"] for s in steps)

    completed_at: Optional[str] = None
    if all_complete:
        # Max of the per-step signal timestamps. Step 2 shares step 3's.
        # Columns mix naive (tracker, mission) and aware (card_progress) —
        # strip tz before comparison so max() doesn't choke on cross-kind
        # comparison.
        ts_candidates = [
            sig.scan_at,
            sig.first_card_progress_at,
            sig.first_card_progress_at,
            sig.mission_at,
            sig.first_review_at,
        ]
        normalized = [
            t.replace(tzinfo=None) if t is not None and t.tzinfo is not None else t
            for t in ts_candidates
        ]
        latest = max(t for t in normalized if t is not None)
        completed_at = latest.isoformat()

    return {
        "steps": steps,
        "all_complete": all_complete,
        "completed_at": completed_at,
    }
