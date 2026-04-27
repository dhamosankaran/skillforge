"""phase6 foundation schema (decks, lessons, quiz_items, quiz_item_progress)

Revision ID: 57951e9f4cdc
Revises: 30bf39fa04f8
Create Date: 2026-04-26

Spec: docs/specs/phase-6/01-foundation-schema.md

Ships the four foundation tables for Phase 6's content lifecycle platform:
  - `decks`             — 12 top-level curriculum buckets (replaces categories
                          for Phase 6 content; legacy `categories` stays)
  - `lessons`           — unit of teaching content (concept_md / production_md
                          / examples_md), one per Learn-page card
  - `quiz_items`        — atomic FSRS-reviewable recall units owned by a lesson
  - `quiz_item_progress`— per-user FSRS state, byte-identical to card_progress
                          modulo the FK swap (D-1, AC-6)

Locked decisions reflected in this migration (spec §11):
  D-1: quiz_item_progress.due_date is NOT NULL with server_default=now() —
       mirrors card_progress.due_date so daily-review WHERE clauses need no
       null branch.
  D-2: lessons.source_content_id ships as String(36) NULLABLE WITHOUT FK
       constraint — slice 6.9 adds the FK once `source_content` exists.
  D-3: ENUM-as-String storage everywhere (no Postgres-native ENUMs).
  D-4: Float for FSRS columns; Numeric(3,2) for lessons.quality_score.
  D-5: archived_at on decks/lessons; retired_at + superseded_by_id (self-FK)
       on quiz_items; no soft-delete on quiz_item_progress.

AC-7: legacy `cards`, `categories`, `card_progress`, `card_feedback` are
NOT touched here. Their drop is deferred to slice 6.15 cleanup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "57951e9f4cdc"
down_revision: Union[str, Sequence[str], None] = "30bf39fa04f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------------------
    # decks
    # ---------------------------------------------------------------------
    op.create_table(
        "decks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("icon", sa.String(length=10), nullable=True),
        sa.Column(
            "persona_visibility",
            sa.String(length=20),
            nullable=False,
            server_default="both",
        ),
        sa.Column(
            "tier",
            sa.String(length=20),
            nullable=False,
            server_default="premium",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_decks_slug"),
    )
    op.create_index(
        "ix_decks_persona_display_active",
        "decks",
        ["persona_visibility", "display_order"],
        postgresql_where=sa.text("archived_at IS NULL"),
    )

    # ---------------------------------------------------------------------
    # lessons
    # ---------------------------------------------------------------------
    op.create_table(
        "lessons",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("deck_id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("concept_md", sa.Text(), nullable=False),
        sa.Column("production_md", sa.Text(), nullable=False),
        sa.Column("examples_md", sa.Text(), nullable=False),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "version_type",
            sa.String(length=20),
            nullable=False,
            server_default="initial",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_by_model", sa.String(length=64), nullable=True),
        # D-2: NULLABLE String(36) WITHOUT FK constraint at this revision.
        sa.Column("source_content_id", sa.String(length=36), nullable=True),
        sa.Column("quality_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["deck_id"], ["decks.id"],
            name="fk_lessons_deck_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("deck_id", "slug", name="uq_lessons_deck_slug"),
    )
    op.create_index("ix_lessons_deck_id", "lessons", ["deck_id"])
    op.create_index(
        "ix_lessons_deck_display_active",
        "lessons",
        ["deck_id", "display_order"],
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_index(
        "ix_lessons_review_queue",
        "lessons",
        ["published_at"],
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.create_index(
        "ix_lessons_deck_archived",
        "lessons",
        ["deck_id", "archived_at"],
    )
    op.create_index(
        "ix_lessons_source_content",
        "lessons",
        ["source_content_id"],
    )

    # ---------------------------------------------------------------------
    # quiz_items (self-referential FK on superseded_by_id)
    # ---------------------------------------------------------------------
    op.create_table(
        "quiz_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("lesson_id", sa.String(length=36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "question_type",
            sa.String(length=20),
            nullable=False,
            server_default="free_text",
        ),
        sa.Column("distractors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "difficulty",
            sa.String(length=10),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("superseded_by_id", sa.String(length=36), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_by_model", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"],
            name="fk_quiz_items_lesson_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"], ["quiz_items.id"],
            name="fk_quiz_items_superseded_by_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_quiz_items_lesson_id", "quiz_items", ["lesson_id"])
    op.create_index(
        "ix_quiz_items_lesson_active_order",
        "quiz_items",
        ["lesson_id", "display_order"],
        postgresql_where=sa.text("retired_at IS NULL"),
    )
    op.create_index(
        "ix_quiz_items_superseded_by",
        "quiz_items",
        ["superseded_by_id"],
    )

    # ---------------------------------------------------------------------
    # quiz_item_progress — byte-identical to card_progress modulo FK swap
    # ---------------------------------------------------------------------
    op.create_table(
        "quiz_item_progress",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("quiz_item_id", sa.String(length=36), nullable=False),
        sa.Column(
            "state",
            sa.String(length=20),
            nullable=False,
            server_default="new",
        ),
        sa.Column("stability", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "difficulty_fsrs",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "elapsed_days",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "scheduled_days",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("reps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fsrs_step", sa.Integer(), nullable=True),
        sa.Column("last_reviewed", sa.DateTime(timezone=True), nullable=True),
        # D-1: NOT NULL with server_default=now() — mirrors card_progress.due_date.
        sa.Column(
            "due_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_quiz_item_progress_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_item_id"], ["quiz_items.id"],
            name="fk_quiz_item_progress_quiz_item_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "quiz_item_id", name="uq_quiz_item_progress_user_quiz"
        ),
    )
    op.create_index(
        "ix_quiz_item_progress_user_id",
        "quiz_item_progress",
        ["user_id"],
    )
    op.create_index(
        "ix_quiz_item_progress_quiz_item_id",
        "quiz_item_progress",
        ["quiz_item_id"],
    )
    op.create_index(
        "ix_quiz_item_progress_user_due",
        "quiz_item_progress",
        ["user_id", "due_date"],
    )
    op.create_index(
        "ix_quiz_item_progress_quiz_item",
        "quiz_item_progress",
        ["quiz_item_id"],
    )


def downgrade() -> None:
    # Drop in reverse FK-dependency order.
    op.drop_index("ix_quiz_item_progress_quiz_item", table_name="quiz_item_progress")
    op.drop_index("ix_quiz_item_progress_user_due", table_name="quiz_item_progress")
    op.drop_index("ix_quiz_item_progress_quiz_item_id", table_name="quiz_item_progress")
    op.drop_index("ix_quiz_item_progress_user_id", table_name="quiz_item_progress")
    op.drop_table("quiz_item_progress")

    op.drop_index("ix_quiz_items_superseded_by", table_name="quiz_items")
    op.drop_index("ix_quiz_items_lesson_active_order", table_name="quiz_items")
    op.drop_index("ix_quiz_items_lesson_id", table_name="quiz_items")
    op.drop_table("quiz_items")

    op.drop_index("ix_lessons_source_content", table_name="lessons")
    op.drop_index("ix_lessons_deck_archived", table_name="lessons")
    op.drop_index("ix_lessons_review_queue", table_name="lessons")
    op.drop_index("ix_lessons_deck_display_active", table_name="lessons")
    op.drop_index("ix_lessons_deck_id", table_name="lessons")
    op.drop_table("lessons")

    op.drop_index("ix_decks_persona_display_active", table_name="decks")
    op.drop_table("decks")
