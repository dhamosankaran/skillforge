"""initial postgres schema with pgvector

Revision ID: 0001_pg_init
Revises:
Create Date: 2026-04-07

This is the first PostgreSQL-native migration. It enables the ``vector``
extension (pgvector) and creates all application tables.

INTENTIONAL DEFERRALS — do not "fix" these without a matching spec:

* id columns use VARCHAR(36), not native UUID.
  ``UUIDPrimaryKeyMixin.id`` is ``Mapped[str]`` throughout the ORM.
  Promoting to native UUID requires changing the mixin, every model, and
  every foreign key in the same commit — that is a separate Phase-0 spec.

* DateTime columns use TIMESTAMP WITHOUT TIME ZONE, not TIMESTAMPTZ.
  The ORM uses timezone-naive ``DateTime`` + ``func.now()``.  Promotion
  to TIMESTAMPTZ must happen alongside switching every ``datetime.utcnow()``
  call to ``datetime.now(timezone.utc)`` — also a separate spec.

EMBEDDING:
  ``resumes.embedding`` is ``vector(1536)``, nullable.  Existing rows carry
  NULL until a Phase-1 backfill job populates them.  The ``vector`` extension
  is enabled at the top of upgrade() before any table is created.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "0001_pg_init"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector. Required by Phase-1 features; harmless here.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("google_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plan", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_customer_id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )
    op.create_index(
        "ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_payment_intent_id"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)

    op.create_table(
        "resumes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("optimized_content", sa.Text(), nullable=True),
        sa.Column("template_type", sa.String(length=50), nullable=True),
        # Nullable until the Phase-1 backfill job populates existing rows.
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"], unique=False)

    op.create_table(
        "usage_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("feature_used", sa.String(length=100), nullable=False),
        sa.Column("tokens_consumed", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_usage_logs_created_at", "usage_logs", ["created_at"], unique=False
    )
    op.create_index("ix_usage_logs_user_id", "usage_logs", ["user_id"], unique=False)

    op.create_table(
        "tracker_applications_v2",
        sa.Column("id", sa.String(length=36), nullable=False),
        # Nullable so unauthenticated tracker rows still work.
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("company", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=200), nullable=False),
        sa.Column("date_applied", sa.String(length=20), nullable=False),
        sa.Column("ats_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tracker_applications_v2_user_id",
        "tracker_applications_v2",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema.

    WARNING: ``DROP EXTENSION vector`` will break any other database
    consumer that depends on pgvector. Only run this on a dedicated
    HirePort database.
    """
    op.drop_index(
        "ix_tracker_applications_v2_user_id", table_name="tracker_applications_v2"
    )
    op.drop_table("tracker_applications_v2")

    op.drop_index("ix_usage_logs_user_id", table_name="usage_logs")
    op.drop_index("ix_usage_logs_created_at", table_name="usage_logs")
    op.drop_table("usage_logs")

    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_table("resumes")

    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP EXTENSION IF EXISTS vector")
