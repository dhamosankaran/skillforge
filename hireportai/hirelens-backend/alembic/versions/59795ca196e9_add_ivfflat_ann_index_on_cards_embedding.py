"""add IVFFlat ANN index on cards.embedding

Revision ID: 59795ca196e9
Revises: d16ca29a5d08
Create Date: 2026-04-17 06:42:32.924722

IVFFlat chosen over HNSW because production pgvector version is unverified.
Swap to HNSW when prod is confirmed >= 0.5.0 and card volume > 1000.
See SESSION-STATE.md DEFERRED-1.

lists = 4 is the sensible floor for the current 15-row deck (usual rule is
sqrt(n_rows); practical minimum is 1-4). Revisit lists when row count grows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59795ca196e9'
down_revision: Union[str, Sequence[str], None] = 'd16ca29a5d08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cards_embedding_ivfflat
        ON cards
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 4)
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_cards_embedding_ivfflat")
