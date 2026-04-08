"""Migration verification tests — Phase-0 PostgreSQL + pgvector.

These tests assert the structural outcomes of the initial Alembic migration:
- all six application tables are present in the test schema
- the pgvector extension is loadable and the vector(n) type round-trips correctly

The ``engine`` and ``db_session`` fixtures live in conftest.py.  They
auto-skip when ``TEST_DATABASE_URL`` is unreachable, so this file is safe
to include in CI without a live database.

``pytestmark`` sets loop_scope="session" for every test in this module so that
test functions run in the same event loop as the session-scoped ``engine`` and
``db_session`` fixtures.  Without this, SQLAlchemy raises
"Future attached to a different loop" because the connection pool is pinned to
the session loop while pytest-asyncio defaults test bodies to the function loop.
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import inspect

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# AC-2: all six tables exist
# ---------------------------------------------------------------------------
EXPECTED_TABLES = {
    "users",
    "subscriptions",
    "payments",
    "resumes",
    "usage_logs",
    "tracker_applications_v2",
}


async def test_tables_exist(engine):
    """All six ORM tables are present after create_all."""
    def _get_table_names(conn):
        return set(inspect(conn).get_table_names())

    async with engine.connect() as conn:
        present = await conn.run_sync(_get_table_names)

    missing = EXPECTED_TABLES - present
    assert not missing, f"Missing tables: {missing}"


# ---------------------------------------------------------------------------
# AC-2 + AC-8: pgvector round-trip
# ---------------------------------------------------------------------------
async def test_vector_roundtrip(db_session):
    """A vector(3) value survives an insert/select cycle.

    pgvector normalises the text representation: [1.0,2.0,3.0] is stored and
    returned as [1,2,3] (trailing zeros dropped, no spaces).
    """
    await db_session.execute(
        sa.text("CREATE TEMP TABLE tmp_vec (id int, embedding vector(3))")
    )
    await db_session.execute(
        sa.text("INSERT INTO tmp_vec VALUES (1, '[1.0,2.0,3.0]')")
    )
    result = await db_session.execute(
        sa.text("SELECT embedding::text FROM tmp_vec WHERE id = 1")
    )
    assert result.scalar_one() == "[1,2,3]"
