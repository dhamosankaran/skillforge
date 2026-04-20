"""add paywall_dismissals and user.downgraded_at

Revision ID: 1176cc179bf0
Revises: f3350dcba3a5
Create Date: 2026-04-20 13:55:51.010839

Spec #42 — paywall dismissal + (deferred) win-back. Dismissal rows
are keyed (user_id, trigger, dismissed_at DESC) for the <50ms
should-show-paywall query. `users.downgraded_at` lands now even
though the win-back consumer is deferred — the column is impossible
to backfill correctly after real downgrades start happening, so we
add it up front.

Note: the autogenerate output also wanted to drop
`ix_cards_category_id_active` and `ix_cards_embedding_ivfflat`
because those indexes exist on the database but are not declared on
the `Card` ORM model. They were added by earlier migrations
(d16ca29a5d08 and predecessors) and remain live — those drops are
false positives and have been scrubbed out of this migration (same
treatment as `f3350dcba3a5`).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1176cc179bf0'
down_revision: Union[str, Sequence[str], None] = 'f3350dcba3a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'paywall_dismissals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('trigger', sa.String(length=64), nullable=False),
        sa.Column(
            'dismissed_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('action_count_at_dismissal', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_paywall_dismissals_user_trigger_time',
        'paywall_dismissals',
        ['user_id', 'trigger', 'dismissed_at'],
        unique=False,
    )
    op.add_column(
        'users',
        sa.Column('downgraded_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'downgraded_at')
    op.drop_index(
        'ix_paywall_dismissals_user_trigger_time',
        table_name='paywall_dismissals',
    )
    op.drop_table('paywall_dismissals')
