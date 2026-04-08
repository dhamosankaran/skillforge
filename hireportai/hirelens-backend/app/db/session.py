"""Async SQLAlchemy engine and session factory (PostgreSQL + asyncpg)."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables():
    """Create all ORM tables (dev convenience — use Alembic in production)."""
    from app.models.base import Base  # noqa: F401 — trigger model registration
    # Import all models so they register with Base.metadata
    import app.models.user  # noqa: F401
    import app.models.subscription  # noqa: F401
    import app.models.payment  # noqa: F401
    import app.models.resume_model  # noqa: F401
    import app.models.usage_log  # noqa: F401
    import app.models.tracker  # noqa: F401

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
