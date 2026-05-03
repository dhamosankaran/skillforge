"""add subscriptions.cancel_at_period_end (B-116)

Revision ID: c2ba25f1d9a7
Revises: c2b8a4d9e6f1
Create Date: 2026-05-03

Audit F-2: ``customer.subscription.updated`` was unhandled, so the
"cancel scheduled" state from the Stripe billing portal never reached
the DB. New ``cancel_at_period_end`` boolean lets the new handler
record the pending cancellation without flipping the user off Pro
before the period actually ends. ``current_period_end`` already exists
on the model and is repurposed by the same handler (audit F-4).

Server-default ``false`` so existing rows backfill safely; column is
NOT NULL so handler reads never need a None branch.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2ba25f1d9a7"
down_revision: Union[str, Sequence[str], None] = "c2b8a4d9e6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "cancel_at_period_end")
