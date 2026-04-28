"""phase6 analytics event tables (quiz_review_events, lesson_view_events)

Revision ID: b8a9d4f3e2c1
Revises: 57951e9f4cdc
Create Date: 2026-04-27

Spec: docs/specs/phase-6/00-analytics-tables.md

Ships the two Postgres event tables that power the Phase 6 SQL-queryable
content-quality / retention dashboards (locked decision I1; spec #38 banned
the PostHog Query API in /admin/analytics):

  - `quiz_review_events`  — one row per FSRS quiz review (BE dual-write).
  - `lesson_view_events`  — one row per lesson page view (FE-emitted via
                             POST /api/v1/lessons/:id/view-event).

Both tables are append-only at runtime (§4.4 + AC-10): the
`analytics_event_service` exposes only `write_*` functions; no UPDATE / DELETE
methods exist. A future retention slice will add a periodic purge job
outside the request path.

Locked FK ON DELETE shapes (§4.3, D-1):
  - `user_id`              ON DELETE SET NULL  (anonymize on account delete;
                                                preserve aggregate rollups)
  - `quiz_item_id`         ON DELETE CASCADE   (no analytical anchor without it)
  - `lesson_id`            ON DELETE CASCADE   (same)
  - `deck_id`              ON DELETE CASCADE   (same)

Denormalization (D-8): `lesson_id` + `deck_id` denormalized on
`quiz_review_events`; `deck_id` denormalized on `lesson_view_events`. JOINs
on per-lesson / per-deck rollups would otherwise hit 3-table joins on every
dashboard query. Lesson IDs are stable (slice 6.4 D-17 — substantive edits
bump `lessons.version`, not `lessons.id`).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8a9d4f3e2c1"
down_revision: Union[str, Sequence[str], None] = "57951e9f4cdc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------------------
    # quiz_review_events (§4.1)
    # ---------------------------------------------------------------------
    op.create_table(
        "quiz_review_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("quiz_item_id", sa.String(length=36), nullable=False),
        sa.Column("lesson_id", sa.String(length=36), nullable=False),
        sa.Column("deck_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("fsrs_state_before", sa.String(length=20), nullable=False),
        sa.Column("fsrs_state_after", sa.String(length=20), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("lapses", sa.Integer(), nullable=False),
        sa.Column(
            "time_spent_ms",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("plan", sa.String(length=20), nullable=True),
        sa.Column("persona", sa.String(length=30), nullable=True),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_quiz_review_events_user_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_item_id"], ["quiz_items.id"],
            name="fk_quiz_review_events_quiz_item_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"],
            name="fk_quiz_review_events_lesson_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deck_id"], ["decks.id"],
            name="fk_quiz_review_events_deck_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_quiz_review_events_user_reviewed_at",
        "quiz_review_events",
        ["user_id", "reviewed_at"],
    )
    op.create_index(
        "ix_quiz_review_events_quiz_item_reviewed_at",
        "quiz_review_events",
        ["quiz_item_id", "reviewed_at"],
    )
    op.create_index(
        "ix_quiz_review_events_lesson_reviewed_at",
        "quiz_review_events",
        ["lesson_id", "reviewed_at"],
    )
    op.create_index(
        "ix_quiz_review_events_deck_reviewed_at",
        "quiz_review_events",
        ["deck_id", "reviewed_at"],
    )

    # ---------------------------------------------------------------------
    # lesson_view_events (§4.2)
    # ---------------------------------------------------------------------
    op.create_table(
        "lesson_view_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("lesson_id", sa.String(length=36), nullable=False),
        sa.Column("deck_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("plan", sa.String(length=20), nullable=True),
        sa.Column("persona", sa.String(length=30), nullable=True),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_lesson_view_events_user_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"],
            name="fk_lesson_view_events_lesson_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deck_id"], ["decks.id"],
            name="fk_lesson_view_events_deck_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_lesson_view_events_user_viewed_at",
        "lesson_view_events",
        ["user_id", "viewed_at"],
    )
    op.create_index(
        "ix_lesson_view_events_lesson_viewed_at",
        "lesson_view_events",
        ["lesson_id", "viewed_at"],
    )
    op.create_index(
        "ix_lesson_view_events_deck_viewed_at",
        "lesson_view_events",
        ["deck_id", "viewed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lesson_view_events_deck_viewed_at",
        table_name="lesson_view_events",
    )
    op.drop_index(
        "ix_lesson_view_events_lesson_viewed_at",
        table_name="lesson_view_events",
    )
    op.drop_index(
        "ix_lesson_view_events_user_viewed_at",
        table_name="lesson_view_events",
    )
    op.drop_table("lesson_view_events")

    op.drop_index(
        "ix_quiz_review_events_deck_reviewed_at",
        table_name="quiz_review_events",
    )
    op.drop_index(
        "ix_quiz_review_events_lesson_reviewed_at",
        table_name="quiz_review_events",
    )
    op.drop_index(
        "ix_quiz_review_events_quiz_item_reviewed_at",
        table_name="quiz_review_events",
    )
    op.drop_index(
        "ix_quiz_review_events_user_reviewed_at",
        table_name="quiz_review_events",
    )
    op.drop_table("quiz_review_events")
