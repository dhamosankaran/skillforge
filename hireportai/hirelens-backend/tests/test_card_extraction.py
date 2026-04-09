"""Integration tests for the card extraction + embedding pipeline.

These tests connect to the DEVELOPMENT database (DATABASE_URL, not
TEST_DATABASE_URL) to verify that:

  1. Cards were seeded by scripts/extract_cards.py
  2. Every card has a non-null embedding after scripts/generate_embeddings.py

Pre-conditions:
  python scripts/extract_cards.py
  python scripts/generate_embeddings.py

The fixtures skip gracefully when the dev DB is unreachable so that these
tests do not block CI runs that lack a local PostgreSQL instance.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Dev DB (not the isolated test DB used by conftest.py) ──────────────────
DEV_DB_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport",
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def dev_engine():
    """Session-scoped engine pointed at the dev (not test) database."""
    eng = create_async_engine(DEV_DB_URL, pool_pre_ping=True)
    try:
        async with eng.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
    except Exception as exc:
        await eng.dispose()
        pytest.skip(f"Dev DB not reachable at {DEV_DB_URL}: {exc}")
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def dev_session(dev_engine) -> AsyncSession:
    """Read-only session for the dev database — never commits."""
    factory = async_sessionmaker(dev_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


# ── Tests ───────────────────────────────────────────────────────────────────

async def test_cards_seeded(dev_session: AsyncSession) -> None:
    """At least one card must exist (extract_cards.py has been run)."""
    result = await dev_session.execute(sa.text("SELECT count(*) FROM cards"))
    count = result.scalar_one()
    assert count > 0, (
        "No cards found in the dev database. "
        "Run: python scripts/extract_cards.py"
    )


async def test_categories_seeded(dev_session: AsyncSession) -> None:
    """At least one category must exist alongside the cards."""
    result = await dev_session.execute(sa.text("SELECT count(*) FROM categories"))
    count = result.scalar_one()
    assert count > 0, (
        "No categories found in the dev database. "
        "Run: python scripts/extract_cards.py"
    )


async def test_all_cards_have_embeddings(dev_session: AsyncSession) -> None:
    """Every card row must have a non-null embedding vector.

    Fails with a clear message if generate_embeddings.py has not been run yet,
    or if any card's embedding was not persisted correctly.
    """
    total = (
        await dev_session.execute(sa.text("SELECT count(*) FROM cards"))
    ).scalar_one()

    with_embedding = (
        await dev_session.execute(
            sa.text("SELECT count(*) FROM cards WHERE embedding IS NOT NULL")
        )
    ).scalar_one()

    missing = total - with_embedding
    assert missing == 0, (
        f"{missing} of {total} card(s) still have NULL embedding. "
        "Run: python scripts/generate_embeddings.py"
    )


async def test_embedding_dimensionality(dev_session: AsyncSession) -> None:
    """Spot-check that at least one stored embedding has 1536 dimensions."""
    result = await dev_session.execute(
        sa.text(
            "SELECT vector_dims(embedding) AS dims "
            "FROM cards WHERE embedding IS NOT NULL LIMIT 1"
        )
    )
    row = result.fetchone()
    assert row is not None, "No embedded cards found."
    assert row[0] == 1536, (
        f"Expected 1536-dim embedding, got {row[0]}. "
        "Check EMBEDDING_DIMS in scripts/generate_embeddings.py."
    )
