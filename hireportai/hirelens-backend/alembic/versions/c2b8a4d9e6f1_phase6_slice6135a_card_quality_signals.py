"""phase 6 slice 6.13.5a card_quality_signals table (B-094a)

Revision ID: c2b8a4d9e6f1
Revises: f1a2b3c4d5e6
Create Date: 2026-05-02

Spec: docs/specs/phase-6/12-quality-signals.md §5.1 + §7 + §12 D-1..D-14.

Greenfield: one new table ``card_quality_signals`` per LD J2 key shape
``(id, lesson_id, quiz_item_id NULLABLE, signal_source, dimension)``
extended with ``recorded_by_user_id`` per §12 D-5 (5-tuple UNIQUE
NULLS-distinct so per-user thumbs rows don't collide).

UPSERT semantics per §12 D-8: ``INSERT ... ON CONFLICT (...) DO UPDATE``
on the UNIQUE key. The UNIQUE constraint is created with ``NULLS NOT
DISTINCT`` (Postgres 15+) so critique rows (where both ``quiz_item_id``
and ``recorded_by_user_id`` are NULL) re-conflict on subsequent
UPSERTs and per-quiz_item user-aggregate rows (where
``recorded_by_user_id`` is NULL) likewise. Per-user thumbs rows stay
distinct by their non-NULL ``recorded_by_user_id``. Append-only audit
trail lives in R2 critique.json (slice 6.10 forever-retention) +
``quiz_review_events`` (slice 6.0 append-only).

FK ON DELETE rules per §5.1:
- ``lesson_id`` CASCADE — signal loses anchor on hard-delete.
- ``quiz_item_id`` CASCADE — same.
- ``recorded_by_user_id`` SET NULL — anonymise on user account deletion;
  preserve aggregate signal value.

Indexes:
- ``ux_card_quality_signals_key`` (UNIQUE, NULLS NOT DISTINCT) on the
  5-tuple — created via raw DDL since SQLAlchemy 2.0's
  ``UniqueConstraint`` does not yet emit Postgres 15's
  ``NULLS NOT DISTINCT`` modifier.
- ``ix_card_quality_signals_lesson_source`` for per-lesson rollups.
- ``ix_card_quality_signals_quiz_item_source`` partial WHERE quiz_item_id
  IS NOT NULL for per-quiz_item rollups.
- ``ix_card_quality_signals_user`` partial WHERE recorded_by_user_id IS
  NOT NULL for "has this user thumbed this lesson" lookups.

``down_revision='f1a2b3c4d5e6'`` confirmed at impl Step 0 per §12 D-14
(``alembic heads`` returned single head ``f1a2b3c4d5e6`` from slice 6.13).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2b8a4d9e6f1"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "card_quality_signals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lesson_id", sa.String(length=36), nullable=False),
        sa.Column("quiz_item_id", sa.String(length=36), nullable=True),
        sa.Column("signal_source", sa.String(length=20), nullable=False),
        sa.Column("dimension", sa.String(length=30), nullable=False),
        sa.Column("score", sa.Numeric(4, 2), nullable=False),
        sa.Column("source_ref", sa.String(length=36), nullable=True),
        sa.Column("recorded_by_user_id", sa.String(length=36), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"],
            name="fk_card_quality_signals_lesson_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_item_id"], ["quiz_items.id"],
            name="fk_card_quality_signals_quiz_item_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"], ["users.id"],
            name="fk_card_quality_signals_recorded_by_user_id",
            ondelete="SET NULL",
        ),
    )

    # NULLS NOT DISTINCT: critique rows (NULL quiz_item_id, NULL
    # recorded_by_user_id) re-conflict on UPSERT; per-quiz_item
    # user_review rows (NULL recorded_by_user_id) likewise; per-user
    # thumbs rows stay distinct via their non-NULL recorded_by_user_id.
    op.execute(
        "ALTER TABLE card_quality_signals "
        "ADD CONSTRAINT ux_card_quality_signals_key UNIQUE NULLS NOT DISTINCT "
        "(lesson_id, quiz_item_id, signal_source, dimension, recorded_by_user_id)"
    )
    op.create_index(
        "ix_card_quality_signals_lesson_source",
        "card_quality_signals",
        ["lesson_id", "signal_source", sa.text("recorded_at DESC")],
    )
    op.create_index(
        "ix_card_quality_signals_quiz_item_source",
        "card_quality_signals",
        ["quiz_item_id", "signal_source", sa.text("recorded_at DESC")],
        postgresql_where=sa.text("quiz_item_id IS NOT NULL"),
    )
    op.create_index(
        "ix_card_quality_signals_user",
        "card_quality_signals",
        ["recorded_by_user_id", "signal_source", sa.text("recorded_at DESC")],
        postgresql_where=sa.text("recorded_by_user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_card_quality_signals_user", table_name="card_quality_signals"
    )
    op.drop_index(
        "ix_card_quality_signals_quiz_item_source",
        table_name="card_quality_signals",
    )
    op.drop_index(
        "ix_card_quality_signals_lesson_source",
        table_name="card_quality_signals",
    )
    op.drop_table("card_quality_signals")
