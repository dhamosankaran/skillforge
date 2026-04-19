"""add interview_question_sets table

Revision ID: f3350dcba3a5
Revises: 02bf7265b387
Create Date: 2026-04-19 13:24:20.316841

Spec #49 — per-JD interview question cache. Keyed on (user_id, jd_hash).

Note: the autogenerate output also wanted to drop `ix_cards_category_id_active`
and `ix_cards_embedding_ivfflat` because those indexes exist on the database
but are not declared on the `Card` ORM model. They were added by earlier
migrations (d16ca29a5d08 and predecessors) and remain live — those drops are
false positives and have been scrubbed out of this migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f3350dcba3a5'
down_revision: Union[str, Sequence[str], None] = '02bf7265b387'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'interview_question_sets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('jd_hash', sa.String(length=64), nullable=False),
        sa.Column('jd_text', sa.Text(), nullable=False),
        sa.Column('questions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('model_used', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'jd_hash', name='uq_interview_sets_user_jd'),
    )
    op.create_index(
        op.f('ix_interview_question_sets_user_id'),
        'interview_question_sets',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_interview_question_sets_user_id'),
        table_name='interview_question_sets',
    )
    op.drop_table('interview_question_sets')
