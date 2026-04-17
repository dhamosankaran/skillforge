"""add email_preferences table

Revision ID: c9863b51075d
Revises: 802d5ba2e219
Create Date: 2026-04-10 05:47:24.463632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9863b51075d'
down_revision: Union[str, Sequence[str], None] = '802d5ba2e219'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('email_preferences',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('daily_reminder', sa.Boolean(), nullable=False),
    sa.Column('timezone', sa.String(length=50), nullable=False),
    sa.Column('unsubscribe_token', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('unsubscribe_token')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('email_preferences')
