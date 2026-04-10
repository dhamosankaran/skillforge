"""Shared pytest fixtures for the HirePort backend.

Integration tests that touch the database use ``db_session``.  If
``TEST_DATABASE_URL`` is unreachable the ``engine`` fixture calls
``pytest.skip`` so the whole session is skipped gracefully — unit tests
(test_nlp, test_parser, test_scorer) still run on machines without a local
PostgreSQL instance because they never request ``engine`` or ``db_session``.

Loop-scope note
---------------
Both ``engine`` and ``db_session`` use ``loop_scope="session"`` so they share
the single session-level event loop created by pytest-asyncio 1.x.  Mixing
loop scopes (engine=session, db_session=function) causes
"Future attached to a different loop" errors because the SQLAlchemy connection
pool is bound to whichever loop created it.
"""
from __future__ import annotations

import os
from typing import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Connection URL
# ---------------------------------------------------------------------------
# Defaults to a *separate* database from the dev DB so tests never touch real
# data.  Override with TEST_DATABASE_URL in CI (set it to a disposable DB spun
# up by the CI service container).
TEST_DATABASE_URL: str = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport_test",
)


# ---------------------------------------------------------------------------
# Engine — session-scoped, creates schema once per test run
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    """Async engine backed by the test database.

    Lifecycle:
    1. Attempt a ``SELECT 1`` — skip the whole session if the DB is down.
    2. Enable the ``vector`` extension (idempotent; requires the hireport user
       to have SUPERUSER or the extension to already be installed).
    3. Create all ORM tables via ``Base.metadata.create_all``.
    4. Yield the engine to every fixture/test that depends on it.
    5. Drop all ORM tables on teardown so the next run starts clean.
    """
    eng = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    # --- reachability check --------------------------------------------------
    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover – environment-dependent
        await eng.dispose()
        pytest.skip(
            f"PostgreSQL test DB not reachable at {TEST_DATABASE_URL}: {exc}"
        )

    # --- pgvector extension --------------------------------------------------
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # --- schema creation -----------------------------------------------------
    # Import Base first, then every model module so their Table objects are
    # registered with Base.metadata before create_all is called.
    from app.models.base import Base
    import app.models.user          # noqa: F401
    import app.models.subscription  # noqa: F401
    import app.models.payment       # noqa: F401
    import app.models.resume_model  # noqa: F401
    import app.models.usage_log     # noqa: F401
    import app.models.tracker       # noqa: F401
    import app.models.category      # noqa: F401
    import app.models.card          # noqa: F401
    import app.models.card_progress  # noqa: F401
    import app.models.gamification       # noqa: F401
    import app.models.mission            # noqa: F401
    import app.models.email_preference   # noqa: F401
    import app.models.card_feedback      # noqa: F401
    import app.models.stripe_event       # noqa: F401

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed the gamification badge catalog. Production seeds it via the alembic
    # migration, but the test schema is built with create_all so we mirror the
    # seed here. Without this, any test that triggers gamification (the new
    # XP wiring inside study_service.review_card) hits an FK violation when
    # award_xp tries to insert a UserBadge row.
    from app.services.gamification_service import BADGES
    async with eng.begin() as conn:
        for b in BADGES:
            await conn.execute(
                text(
                    "INSERT INTO badges (id, name, description, threshold_type, threshold_value) "
                    "VALUES (:id, :name, :desc, :tt, :tv) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": b.id,
                    "name": b.name,
                    "desc": b.name,
                    "tt": b.threshold_type,
                    "tv": b.threshold_value,
                },
            )

    yield eng

    # --- teardown ------------------------------------------------------------
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


# ---------------------------------------------------------------------------
# Session — function-scoped, always rolls back
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(loop_scope="session")
async def db_session(engine) -> AsyncIterator[AsyncSession]:
    """Async database session for a single test.

    Uses ``loop_scope="session"`` (matching the ``engine`` fixture) so both
    run in the same event loop and share the connection pool without errors.

    Each test gets a fresh session whose work is always rolled back on
    teardown — no ``ON CONFLICT`` or manual cleanup needed between tests.
    """
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
