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

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.integration,
]


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
    assert total > 0, (
        "No cards seeded — run scripts/extract_cards.py before this test"
    )

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


async def test_soft_deleted_card_excluded_from_active_queries(
    dev_session: AsyncSession,
) -> None:
    """Soft-deleted cards must be excluded by the canonical WHERE deleted_at IS NULL filter.

    Inserts two cards in the same category — one active, one with a non-null
    deleted_at — then asserts that the canonical active-card filter returns
    only the non-deleted row. The dev_session fixture never commits, so the
    inserts roll back on session close and the dev DB stays clean.
    """
    cat_row = (
        await dev_session.execute(sa.text("SELECT id FROM categories LIMIT 1"))
    ).fetchone()
    assert cat_row is not None, (
        "No categories found — run scripts/extract_cards.py first"
    )
    category_id = cat_row[0]

    active_id = "00000000-0000-0000-0000-0000000a0001"
    deleted_id = "00000000-0000-0000-0000-0000000a0002"

    await dev_session.execute(
        sa.text(
            """
            INSERT INTO cards
                (id, category_id, question, answer, difficulty, tags)
            VALUES
                (:id, :cat, :q, :a, 'Easy', CAST('[]' AS json))
            """
        ),
        {"id": active_id, "cat": category_id, "q": "Q-active", "a": "A-active"},
    )
    await dev_session.execute(
        sa.text(
            """
            INSERT INTO cards
                (id, category_id, question, answer, difficulty, tags, deleted_at)
            VALUES
                (:id, :cat, :q, :a, 'Easy', CAST('[]' AS json), NOW())
            """
        ),
        {"id": deleted_id, "cat": category_id, "q": "Q-deleted", "a": "A-deleted"},
    )

    rows = (
        await dev_session.execute(
            sa.text(
                """
                SELECT id FROM cards
                WHERE id IN (:a, :d) AND deleted_at IS NULL
                """
            ),
            {"a": active_id, "d": deleted_id},
        )
    ).fetchall()

    ids = [r[0] for r in rows]
    assert ids == [active_id], (
        f"Expected only the non-deleted card, got {ids}"
    )

    await dev_session.rollback()


async def test_ivfflat_index_used_in_semantic_search(
    dev_session: AsyncSession,
) -> None:
    """The post-seed IVFFlat ANN index must be chosen by cosine-distance queries.

    Why `SET LOCAL enable_seqscan = OFF` *and* `enable_sort = OFF`:
    with only ~15 rows, PostgreSQL's planner correctly prefers Seq Scan (or a
    cheap B-tree Index Scan + Sort) over an ANN index — ANN only wins at
    scale. Disabling seqscan alone isn't enough because the partial index
    `ix_cards_category_id_active` (from P1-S1a) plus an explicit Sort is still
    cheaper than the ANN index at 15 rows. Disabling both forces the planner
    to pick an index that natively provides the ORDER BY (pgvector's IVFFlat
    is `amcanorderbyop`), which is what we actually want to assert exists and
    is usable. `LOCAL` scopes both overrides to this transaction so global
    settings are untouched.
    """
    await dev_session.execute(sa.text("SET LOCAL enable_seqscan = OFF"))
    await dev_session.execute(sa.text("SET LOCAL enable_sort = OFF"))

    # Single non-zero component keeps cosine distance well-defined (all-zero
    # vectors have undefined cosine similarity) without needing a subquery.
    query_vec = "[1," + ",".join(["0"] * 1535) + "]"

    plan_rows = (
        await dev_session.execute(
            sa.text(
                """
                EXPLAIN
                SELECT id
                FROM cards
                WHERE deleted_at IS NULL
                ORDER BY embedding <=> CAST(:v AS vector)
                LIMIT 5
                """
            ),
            {"v": query_vec},
        )
    ).fetchall()

    plan_text = "\n".join(row[0] for row in plan_rows)
    assert "ix_cards_embedding_ivfflat" in plan_text, (
        "Expected the IVFFlat ANN index to appear in the EXPLAIN plan; "
        f"got:\n{plan_text}"
    )

    await dev_session.rollback()
