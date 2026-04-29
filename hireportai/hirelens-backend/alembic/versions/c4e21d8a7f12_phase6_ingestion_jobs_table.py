"""phase 6 ingestion_jobs table (slice 6.10a)

Revision ID: c4e21d8a7f12
Revises: b8a9d4f3e2c1
Create Date: 2026-04-29

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §5.3 + §7.

Ships the `ingestion_jobs` table that backs the AI ingestion pipeline's
durable job state (G-7). Slice 6.10a (B-083a) ships the schema only;
the orchestrator + worker + admin route that exercise it land with
B-083b.

Locked FK ON DELETE shapes (§5.3 + §7):
  - `created_by_user_id` ON DELETE SET NULL  (admin account deletion
                                              must not orphan history;
                                              mirrors slice 6.0 D-1)
  - `target_deck_id`     ON DELETE SET NULL  (deck deletion does not
                                              orphan ingestion history)

Indexes (§5.3 commentary + §7):
  - `(status, created_at DESC)` — admin "recent jobs" query
  - `(source_content_sha256)`   — content-hash dedupe lookup (D-5)
  - `(created_by_user_id, created_at DESC)` — per-admin filtering
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4e21d8a7f12"
down_revision: Union[str, Sequence[str], None] = "b8a9d4f3e2c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "source_format",
            sa.String(length=16),
            nullable=False,
            server_default="markdown",
        ),
        sa.Column("source_content_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_r2_key", sa.String(length=255), nullable=False),
        sa.Column("draft_r2_key", sa.String(length=255), nullable=True),
        sa.Column("critique_r2_key", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("target_deck_slug", sa.String(length=64), nullable=True),
        sa.Column("target_deck_id", sa.String(length=36), nullable=True),
        sa.Column(
            "generated_lesson_ids",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "generated_quiz_item_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("critique_verdict", sa.String(length=16), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "current_attempt",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_ingestion_jobs_created_by_user_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_deck_id"], ["decks.id"],
            name="fk_ingestion_jobs_target_deck_id",
            ondelete="SET NULL",
        ),
    )
    # Single-column index on `status` per the column-level `index=True` in
    # the ORM model (kept for parity with `quiz_review_events` precedent).
    op.create_index(
        "ix_ingestion_jobs_status",
        "ingestion_jobs",
        ["status"],
    )
    # Composite (status, created_at) for the admin "recent jobs" query.
    op.create_index(
        "ix_ingestion_jobs_status_created_at",
        "ingestion_jobs",
        ["status", "created_at"],
    )
    # Dedupe lookup (B-083b's `enqueue_ingestion` dedupe per D-5).
    op.create_index(
        "ix_ingestion_jobs_source_content_sha256",
        "ingestion_jobs",
        ["source_content_sha256"],
    )
    # Per-admin filtering (`mine_only=true` query param).
    op.create_index(
        "ix_ingestion_jobs_admin_created_at",
        "ingestion_jobs",
        ["created_by_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingestion_jobs_admin_created_at",
        table_name="ingestion_jobs",
    )
    op.drop_index(
        "ix_ingestion_jobs_source_content_sha256",
        table_name="ingestion_jobs",
    )
    op.drop_index(
        "ix_ingestion_jobs_status_created_at",
        table_name="ingestion_jobs",
    )
    op.drop_index(
        "ix_ingestion_jobs_status",
        table_name="ingestion_jobs",
    )
    op.drop_table("ingestion_jobs")
