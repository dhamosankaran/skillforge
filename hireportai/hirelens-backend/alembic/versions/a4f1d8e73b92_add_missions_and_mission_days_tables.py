"""add missions and mission_days tables

Revision ID: a4f1d8e73b92
Revises: 83a02cb65464
Create Date: 2026-04-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4f1d8e73b92'
down_revision: Union[str, Sequence[str], None] = '83a02cb65464'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create missions, mission_categories, and mission_days tables."""
    op.create_table(
        'missions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('daily_target', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_missions_user_id'), 'missions', ['user_id'], unique=False)
    op.create_index(op.f('ix_missions_status'), 'missions', ['status'], unique=False)

    op.create_table(
        'mission_categories',
        sa.Column('mission_id', sa.String(length=36), nullable=False),
        sa.Column('category_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['mission_id'], ['missions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('mission_id', 'category_id'),
    )

    op.create_table(
        'mission_days',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('mission_id', sa.String(length=36), nullable=False),
        sa.Column('day_number', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('cards_target', sa.Integer(), nullable=False),
        sa.Column('cards_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['mission_id'], ['missions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mission_id', 'day_number', name='uq_mission_days_number'),
        sa.UniqueConstraint('mission_id', 'date', name='uq_mission_days_date'),
    )
    op.create_index(op.f('ix_mission_days_mission_id'), 'mission_days', ['mission_id'], unique=False)


def downgrade() -> None:
    """Drop mission tables."""
    op.drop_index(op.f('ix_mission_days_mission_id'), table_name='mission_days')
    op.drop_table('mission_days')
    op.drop_table('mission_categories')
    op.drop_index(op.f('ix_missions_status'), table_name='missions')
    op.drop_index(op.f('ix_missions_user_id'), table_name='missions')
    op.drop_table('missions')
