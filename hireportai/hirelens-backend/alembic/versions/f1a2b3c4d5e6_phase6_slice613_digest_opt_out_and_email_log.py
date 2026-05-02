"""phase 6 slice 6.13 digest opt-out + email_log dedup table (B-087)

Revision ID: f1a2b3c4d5e6
Revises: e043a1b2c3d4
Create Date: 2026-05-01

Spec: docs/specs/phase-6/13-pro-digest-opt-out.md §5.1 + §5.2 + §7.

Additive: one column on ``email_preferences`` + new ``email_log`` table.
Server default ``false`` on the new column means existing rows pick up
``daily_digest_opt_out=False`` without a backfill UPDATE (AC-13).

``email_log`` is the dedup table for the slice 6.14 cron daily Pro
digest. Per §5.2 it supersedes Phase-2 spec #15 §``email_send_log``
(designed but never built); see one-line forward-link header in
``docs/specs/phase-2/15-daily-email.md`` line 162.

FK shape: ``user_id`` ON DELETE CASCADE per OQ-E (orphan rows have
no aggregate value — dedup-only).

Indexes: composite ``(user_id, sent_date)`` mirrors
``ix_quiz_review_events_user_reviewed_at`` shape; supports the
slice 6.14 cron's ``was_sent_today`` short-circuit.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e043a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "email_preferences",
        sa.Column(
            "daily_digest_opt_out",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "email_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("email_type", sa.String(length=30), nullable=False),
        sa.Column("sent_date", sa.Date(), nullable=False),
        sa.Column("resend_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_email_log_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "email_type", "sent_date",
            name="uq_email_log_user_type_date",
        ),
    )
    op.create_index(
        "ix_email_log_user_sent_date",
        "email_log",
        ["user_id", "sent_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_log_user_sent_date", table_name="email_log")
    op.drop_table("email_log")
    op.drop_column("email_preferences", "daily_digest_opt_out")
