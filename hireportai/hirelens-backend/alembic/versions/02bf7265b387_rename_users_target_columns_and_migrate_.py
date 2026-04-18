"""rename users target columns and migrate persona enum values

Revision ID: 02bf7265b387
Revises: 59795ca196e9
Create Date: 2026-04-18 06:46:16.880632

P5-S16 migration. Aligns the users table with the PersonaPicker +
HomeDashboard spec (`docs/specs/phase-5/34-persona-picker-and-home.md`):

  1. Widen users.persona from VARCHAR(20) to VARCHAR(30) for future
     headroom (no current values exceed 17 chars).
  2. Rewrite legacy persona values to the new snake_case set:
       interview -> interview_prepper
       climber   -> career_climber
       team      -> team_lead
  3. Rename users.target_company -> users.interview_target_company and
     narrow it from VARCHAR(255) to VARCHAR(100).
  4. Rename users.target_date -> users.interview_target_date and cast
     it from TIMESTAMP to DATE.

Pre-flight diagnostic (2026-04-18 against dev DB): zero rows with
non-null legacy target_* data, so the type narrowings are lossless.
One row currently holds persona='team' — migrated in place.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02bf7265b387'
down_revision: Union[str, Sequence[str], None] = '59795ca196e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Widen persona column first so all new values fit comfortably.
    op.alter_column(
        'users',
        'persona',
        existing_type=sa.String(length=20),
        type_=sa.String(length=30),
        existing_nullable=True,
    )

    # 2. Migrate legacy persona values in place.
    op.execute(
        "UPDATE users SET persona = 'interview_prepper' WHERE persona = 'interview'"
    )
    op.execute(
        "UPDATE users SET persona = 'career_climber' WHERE persona = 'climber'"
    )
    op.execute(
        "UPDATE users SET persona = 'team_lead' WHERE persona = 'team'"
    )

    # 3. target_company -> interview_target_company (String(255) -> String(100)).
    #    Narrowing is safe because the pre-flight diagnostic found zero
    #    non-null rows; no truncation risk.
    op.alter_column(
        'users',
        'target_company',
        new_column_name='interview_target_company',
        existing_type=sa.String(length=255),
        type_=sa.String(length=100),
        existing_nullable=True,
    )

    # 4. target_date -> interview_target_date (DateTime -> Date).
    #    postgresql_using casts the timestamp to a date; harmless on
    #    nulls and safe given the zero-row diagnostic.
    op.alter_column(
        'users',
        'target_date',
        new_column_name='interview_target_date',
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using='target_date::date',
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse of upgrade, in opposite order.

    # 4. interview_target_date -> target_date (Date -> DateTime).
    op.alter_column(
        'users',
        'interview_target_date',
        new_column_name='target_date',
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        existing_nullable=True,
        postgresql_using='interview_target_date::timestamp',
    )

    # 3. interview_target_company -> target_company (String(100) -> String(255)).
    op.alter_column(
        'users',
        'interview_target_company',
        new_column_name='target_company',
        existing_type=sa.String(length=100),
        type_=sa.String(length=255),
        existing_nullable=True,
    )

    # 2. Reverse the persona value rewrites.
    op.execute(
        "UPDATE users SET persona = 'interview' WHERE persona = 'interview_prepper'"
    )
    op.execute(
        "UPDATE users SET persona = 'climber' WHERE persona = 'career_climber'"
    )
    op.execute(
        "UPDATE users SET persona = 'team' WHERE persona = 'team_lead'"
    )

    # 1. Narrow persona back to String(20).
    op.alter_column(
        'users',
        'persona',
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
