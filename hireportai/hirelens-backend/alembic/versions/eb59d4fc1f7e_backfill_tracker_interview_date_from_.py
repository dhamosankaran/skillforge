"""backfill tracker interview_date from deprecated user fields

Revision ID: eb59d4fc1f7e
Revises: 9543aa466524
Create Date: 2026-04-23 20:40:19.876944

Spec #57 AC-8 — backfill the newly-added
tracker_applications_v2.interview_date column from the deprecated
users.interview_target_date column.

Rule per AC-8:
  For each user U with users.interview_target_date IS NOT NULL:
    Find the most-recent active tracker row:
      WHERE user_id = U.id
        AND status IN ('Applied', 'Interview')
      ORDER BY created_at DESC LIMIT 1
    IF FOUND and its interview_date IS NULL:
      UPDATE that row's interview_date = U.interview_target_date.
      (Never overwrite an existing interview_date — keeps re-runs safe.)
    IF NOT FOUND (no Applied/Interview rows at all):
      INSERT a synthetic tracker row with:
        user_id            = U.id
        company            = COALESCE(U.interview_target_company, 'Unknown')
        role               = 'TBD'
        date_applied       = CURRENT_DATE in ISO yyyy-mm-dd
        status             = 'Interview'
        interview_date     = U.interview_target_date
        ats_score          = 0
        scan_id            = NULL
        skills_matched     = NULL
        skills_missing     = NULL

Downgrade strategy — best effort:
  - DELETE synthetic rows matching the exact shape upgrade() emits:
      role='TBD' AND ats_score=0 AND scan_id IS NULL
      AND status='Interview' AND interview_date IS NOT NULL
    If a user has since hand-edited a synthetic row so it no longer
    matches this fingerprint, downgrade() leaves it alone — that row
    represents legitimate user state.
  - SET interview_date = NULL on non-synthetic rows whose date still
    equals the user's deprecated users.interview_target_date (likely
    came from this backfill's UPDATE branch). Rows where the user has
    since changed the date via the new tracker API won't match and
    are left alone.

  downgrade() is best-effort; it does NOT raise on ambiguous state.
  Operators rolling back long after a deploy should expect some rows
  (ones diverged from the upgrade() fingerprint) to keep their
  interview_date value.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb59d4fc1f7e'
down_revision: Union[str, Sequence[str], None] = '9543aa466524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_UPGRADE_UPDATE_EXISTING = sa.text(
    """
    WITH ranked AS (
        SELECT
            t.id AS tracker_id,
            u.interview_target_date AS user_date,
            ROW_NUMBER() OVER (
                PARTITION BY t.user_id
                ORDER BY t.created_at DESC
            ) AS rn
        FROM tracker_applications_v2 t
        JOIN users u ON u.id = t.user_id
        WHERE u.interview_target_date IS NOT NULL
          AND t.status IN ('Applied', 'Interview')
          AND t.interview_date IS NULL
    )
    UPDATE tracker_applications_v2 AS ta
    SET interview_date = ranked.user_date
    FROM ranked
    WHERE ta.id = ranked.tracker_id
      AND ranked.rn = 1;
    """
)

_UPGRADE_INSERT_SYNTHETIC = sa.text(
    """
    INSERT INTO tracker_applications_v2 (
        id,
        user_id,
        company,
        role,
        date_applied,
        ats_score,
        status,
        scan_id,
        skills_matched,
        skills_missing,
        interview_date,
        created_at
    )
    SELECT
        gen_random_uuid()::text,
        u.id,
        COALESCE(u.interview_target_company, 'Unknown'),
        'TBD',
        to_char(CURRENT_DATE, 'YYYY-MM-DD'),
        0,
        'Interview',
        NULL,
        NULL,
        NULL,
        u.interview_target_date,
        NOW()
    FROM users u
    WHERE u.interview_target_date IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM tracker_applications_v2 t
          WHERE t.user_id = u.id
            AND t.status IN ('Applied', 'Interview')
      );
    """
)

_DOWNGRADE_DELETE_SYNTHETIC = sa.text(
    """
    DELETE FROM tracker_applications_v2
    WHERE role = 'TBD'
      AND ats_score = 0
      AND scan_id IS NULL
      AND status = 'Interview'
      AND interview_date IS NOT NULL;
    """
)

_DOWNGRADE_CLEAR_UPDATED = sa.text(
    """
    UPDATE tracker_applications_v2 AS ta
    SET interview_date = NULL
    FROM users u
    WHERE ta.user_id = u.id
      AND u.interview_target_date IS NOT NULL
      AND ta.interview_date = u.interview_target_date;
    """
)


def upgrade() -> None:
    """Apply the backfill per AC-8."""
    bind = op.get_bind()
    bind.execute(_UPGRADE_UPDATE_EXISTING)
    bind.execute(_UPGRADE_INSERT_SYNTHETIC)


def downgrade() -> None:
    """Best-effort revert — see module docstring for limits."""
    bind = op.get_bind()
    bind.execute(_DOWNGRADE_DELETE_SYNTHETIC)
    bind.execute(_DOWNGRADE_CLEAR_UPDATED)
