"""add interview_date to tracker_applications_v2

Revision ID: 9543aa466524
Revises: 538fe233b639
Create Date: 2026-04-23 20:39:39.471010

Spec #57 (docs/specs/phase-5/57-tracker-level-interview-date.md) — moves
interview target from users.interview_target_date to a per-application
column on tracker_applications_v2. This revision adds the column + a
partial index to keep the countdown read cheap. The data backfill (per
AC-8) ships in a separate revision (see:
backfill_tracker_interview_date.py) so this schema-only step is cleanly
reversible on its own.

Autogen hygiene: Alembic autogen also emitted spurious op.drop_index calls
against cards.ix_cards_category_id_active and cards.ix_cards_embedding_ivfflat
— a known false-positive for partial / vector-opclass indexes (see
.agent/skills/db-migration.md §Gotchas). Those ops have been removed from
this revision; the indexes still exist in the live DB and are not
touched here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9543aa466524'
down_revision: Union[str, Sequence[str], None] = '538fe233b639'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "ix_tracker_apps_user_interview_date"


def upgrade() -> None:
    """Upgrade schema — add interview_date column + partial countdown index."""
    op.add_column(
        "tracker_applications_v2",
        sa.Column("interview_date", sa.Date(), nullable=True),
    )
    op.create_index(
        INDEX_NAME,
        "tracker_applications_v2",
        ["user_id", "interview_date"],
        postgresql_where=sa.text(
            "interview_date IS NOT NULL "
            "AND status IN ('Applied', 'Interview')"
        ),
    )


def downgrade() -> None:
    """Downgrade schema — drop the partial index, then the column."""
    op.drop_index(INDEX_NAME, table_name="tracker_applications_v2")
    op.drop_column("tracker_applications_v2", "interview_date")
