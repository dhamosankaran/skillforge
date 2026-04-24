"""add analysis_payload to tracker_applications_v2

Revision ID: 30bf39fa04f8
Revises: eb59d4fc1f7e
Create Date: 2026-04-24 14:31:17.464760

Spec #59 (docs/specs/phase-5/59-scan-persistence.md) — persist the full
AnalysisResponse per scan so /prep/results can hydrate from URL scan_id
on a fresh session. JSONB NULL; loaded via sqlalchemy.orm.deferred() on
the ORM so GET /tracker list responses stay cheap (LD-2). No backfill —
rows written before this migration stay NULL and trigger 410 Gone from
GET /api/v1/analyze/{scan_id} (LD-5).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '30bf39fa04f8'
down_revision: Union[str, Sequence[str], None] = 'eb59d4fc1f7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add nullable analysis_payload JSONB column."""
    op.add_column(
        "tracker_applications_v2",
        sa.Column(
            "analysis_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema — drop analysis_payload column."""
    op.drop_column("tracker_applications_v2", "analysis_payload")
