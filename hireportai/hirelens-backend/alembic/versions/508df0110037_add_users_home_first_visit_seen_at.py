"""add users.home_first_visit_seen_at

Revision ID: 508df0110037
Revises: 1176cc179bf0
Create Date: 2026-04-22

Adds a nullable `home_first_visit_seen_at` timestamp to `users`. Used by
HomeDashboard to discriminate first-visit vs return-visit greeting copy
(B-016). No backfill: NULL on existing rows is the intended state — the
next `/home` visit stamps it and flips the greeting for that user onward.
`user.onboarding_completed` and the `first_action_seen` localStorage flag
are both unusable for this purpose (both are already true by the time
the user lands on `/home` the first time — see B-016 Notes).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '508df0110037'
down_revision: Union[str, Sequence[str], None] = '1176cc179bf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('home_first_visit_seen_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'home_first_visit_seen_at')
