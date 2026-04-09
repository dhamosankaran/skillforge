"""Alembic env.py — async-compatible for SQLAlchemy + asyncpg (PostgreSQL).

Targets PostgreSQL 16 + pgvector. SQLite-era ``render_as_batch`` mode has
been removed; future migrations may use normal ``ALTER TABLE``.

DATABASE_URL is injected from the environment rather than hardcoded in
alembic.ini.  Set it before invoking alembic, e.g.:

    export DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport
    alembic upgrade head
"""
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject DATABASE_URL from the environment.  Falls back to the dev default so
# `alembic upgrade head` works out of the box on a freshly cloned repo with a
# local PostgreSQL instance set up per CLAUDE.md.
_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport",
)
config.set_main_option("sqlalchemy.url", _DATABASE_URL)

# Import all models so autogenerate can detect them
from app.models.base import Base  # noqa: E402
import app.models.user  # noqa: E402, F401
import app.models.subscription  # noqa: E402, F401
import app.models.payment  # noqa: E402, F401
import app.models.resume_model  # noqa: E402, F401
import app.models.usage_log  # noqa: E402, F401
import app.models.tracker  # noqa: E402, F401
import app.models.category     # noqa: E402, F401
import app.models.card          # noqa: E402, F401
import app.models.card_progress  # noqa: E402, F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
