"""phase 5 e052 user_career_intents (B-125a)

Revision ID: e052b125a4f1
Revises: c2ba25f1d9a7
Create Date: 2026-05-04

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §5.1 + §7.

Additive: one new ``user_career_intents`` table with three composite
indexes. No data backfill — existing users start with zero rows.

FK shape: ``user_id`` ON DELETE CASCADE per spec §5.1 (orphan rows
have no aggregate value once the user is deleted; the longitudinal
narrative is per-user-only).

Indexes:

- ``ix_user_career_intents_user_id`` — drives FK joins.
- ``ix_user_career_intents_user_current`` — drives current-intent
  lookup ``WHERE user_id = ? AND superseded_at IS NULL``.
- ``ix_user_career_intents_bucket_current`` — drives the cohort
  count + aggregate-stats query
  ``WHERE target_role = ? AND target_quarter = ? AND superseded_at
  IS NULL``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e052b125a4f1"
down_revision: Union[str, Sequence[str], None] = "c2ba25f1d9a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_career_intents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("target_role", sa.String(length=30), nullable=False),
        sa.Column("target_quarter", sa.String(length=7), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "superseded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_career_intents_user_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_user_career_intents_user_id",
        "user_career_intents",
        ["user_id"],
    )
    op.create_index(
        "ix_user_career_intents_user_current",
        "user_career_intents",
        ["user_id", "superseded_at"],
    )
    op.create_index(
        "ix_user_career_intents_bucket_current",
        "user_career_intents",
        ["target_role", "target_quarter", "superseded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_career_intents_bucket_current",
        table_name="user_career_intents",
    )
    op.drop_index(
        "ix_user_career_intents_user_current",
        table_name="user_career_intents",
    )
    op.drop_index(
        "ix_user_career_intents_user_id",
        table_name="user_career_intents",
    )
    op.drop_table("user_career_intents")
