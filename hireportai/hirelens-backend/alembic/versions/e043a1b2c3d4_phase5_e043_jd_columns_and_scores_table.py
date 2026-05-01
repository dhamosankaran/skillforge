"""phase 5 E-043 jd columns + tracker_application_scores (slice B-086a)

Revision ID: e043a1b2c3d4
Revises: c4e21d8a7f12
Create Date: 2026-04-30

Spec: docs/specs/phase-5/63-ats-rescan-loop.md §1.3 + §5.3 + §5.4 + §7.

Foundation half of E-043 (B-086a): bundles Q1 LOCKED migration adding
``jd_text`` + ``jd_hash`` columns to ``tracker_applications_v2`` (D-020
closure) AND the new ``tracker_application_scores`` history table (Q2
LOCKED). Both nullable per D-10 (no backfill of pre-migration rows).

The orchestrator + route + worker that exercise these columns land in
B-086b; this migration is foundation only.

D-020 closure line item: ``op.add_column("tracker_applications_v2",
"jd_hash")`` resolves the long-standing drift documented at
SESSION-STATE.md.

FK shapes (§5.3 + spec §7):
  - ``tracker_application_id`` ON DELETE CASCADE  (history dies with
                                                   the tracker row)
  - ``user_id``                ON DELETE CASCADE  (denormalized FK,
                                                   mirrors slice 6.0
                                                   D-1 / D-7)
  - ``scan_id``                ON DELETE SET NULL (preserve history if
                                                   scan row later
                                                   deleted; mirrors
                                                   B-035 P5-S59)

Indexes (§5.3 + §7):
  - ``ix_tracker_apps_jd_hash``                       (D-2 dedupe +
                                                       cross-row JD
                                                       fingerprint)
  - ``ix_tas_tracker_app_scanned_at``                 (chronological
                                                       history fetch)
  - ``ix_tas_user_scanned_at``                        (admin analytics
                                                       "avg score
                                                       improvement")
  - ``ix_tas_dedupe_lookup``                          (D-2 short-
                                                       circuit lookup)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e043a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "c4e21d8a7f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Q1 LOCK (D-020 closure) ──────────────────────────────────────────
    # Add jd_text + jd_hash to tracker_applications_v2. Both nullable per
    # D-10 (no backfill of pre-migration rows; D-9 422 path covers the
    # gap when /rescan hits a row with jd_text=NULL).
    op.add_column(
        "tracker_applications_v2",
        sa.Column("jd_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "tracker_applications_v2",
        sa.Column("jd_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_tracker_apps_jd_hash",
        "tracker_applications_v2",
        ["jd_hash"],
    )

    # ── Q2 LOCK (tracker_application_scores) ─────────────────────────────
    op.create_table(
        "tracker_application_scores",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tracker_application_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("scan_id", sa.String(length=36), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("keyword_match_score", sa.Float(), nullable=False),
        sa.Column("skills_coverage_score", sa.Float(), nullable=False),
        sa.Column(
            "formatting_compliance_score", sa.Float(), nullable=False
        ),
        sa.Column("bullet_strength_score", sa.Float(), nullable=False),
        sa.Column("jd_hash", sa.String(length=64), nullable=False),
        sa.Column("resume_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tracker_application_id"], ["tracker_applications_v2.id"],
            name="fk_tas_tracker_application_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_tas_user_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_tas_tracker_app_scanned_at",
        "tracker_application_scores",
        ["tracker_application_id", "scanned_at"],
    )
    op.create_index(
        "ix_tas_user_scanned_at",
        "tracker_application_scores",
        ["user_id", "scanned_at"],
    )
    op.create_index(
        "ix_tas_dedupe_lookup",
        "tracker_application_scores",
        ["tracker_application_id", "jd_hash", "resume_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tas_dedupe_lookup", table_name="tracker_application_scores"
    )
    op.drop_index(
        "ix_tas_user_scanned_at", table_name="tracker_application_scores"
    )
    op.drop_index(
        "ix_tas_tracker_app_scanned_at",
        table_name="tracker_application_scores",
    )
    op.drop_table("tracker_application_scores")
    op.drop_index(
        "ix_tracker_apps_jd_hash", table_name="tracker_applications_v2"
    )
    op.drop_column("tracker_applications_v2", "jd_hash")
    op.drop_column("tracker_applications_v2", "jd_text")
