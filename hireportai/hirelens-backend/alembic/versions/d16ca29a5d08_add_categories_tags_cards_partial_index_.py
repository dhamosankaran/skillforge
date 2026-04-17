"""add categories.tags + cards partial index for active rows

Revision ID: d16ca29a5d08
Revises: e4eab11b8e33
Create Date: 2026-04-16 22:11:16.338316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd16ca29a5d08'
down_revision: Union[str, Sequence[str], None] = 'e4eab11b8e33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "categories",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_index(
        "ix_cards_category_id_active",
        "cards",
        ["category_id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_cards_category_id_active",
        table_name="cards",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_column("categories", "tags")
