"""Async SQLAlchemy engine and session factory."""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.database_url
        # Ensure the data directory exists for SQLite
        if "sqlite" in db_url:
            db_path = db_url.split("///")[-1]
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        _engine = create_async_engine(
            db_url,
            echo=False,
            # SQLite needs check_same_thread=False for async
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
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
