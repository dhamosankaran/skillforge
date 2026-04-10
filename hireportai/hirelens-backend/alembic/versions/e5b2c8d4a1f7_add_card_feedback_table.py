"""add card_feedback table

Revision ID: e5b2c8d4a1f7
Revises: d3a7e2f91c04
Create Date: 2026-04-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b2c8d4a1f7'
down_revision: Union[str, Sequence[str], None] = 'd3a7e2f91c04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'card_feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('card_id', sa.String(36), sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('vote', sa.String(4), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('card_feedback')
