"""add persona and onboarding_completed to users

Revision ID: d3a7e2f91c04
Revises: b1674f79f780
Create Date: 2026-04-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3a7e2f91c04'
down_revision: Union[str, Sequence[str], None] = 'b1674f79f780'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('persona', sa.String(20), nullable=True))
    op.add_column('users', sa.Column(
        'onboarding_completed',
        sa.Boolean(),
        server_default=sa.text('false'),
        nullable=False,
    ))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'persona')
