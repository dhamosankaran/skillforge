"""Alembic round-trip — slice 6.13 digest opt-out + email_log table.

Spec: docs/specs/phase-6/13-pro-digest-opt-out.md §10.2 + AC-12 + AC-13.

Stamps the test DB to head (asserts the new artifacts are present),
downgrades one revision (drops them), then upgrades back. Mirrors the
``tests/test_e043_jd_columns_migration.py`` precedent — runs alembic
via subprocess so pytest-asyncio doesn't conflict with env.py's
``asyncio.run(...)``.

Marker-gated as integration; the canonical AC-12 check is the shell
round-trip documented in ``db-migration.md``.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import inspect, text

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _table_exists(engine, table: str) -> bool:
    def _collect(conn):
        return table in set(inspect(conn).get_table_names())

    async with engine.connect() as conn:
        return await conn.run_sync(_collect)


async def _column_exists(engine, table: str, column: str) -> bool:
    def _collect(conn):
        cols = {c["name"] for c in inspect(conn).get_columns(table)}
        return column in cols

    async with engine.connect() as conn:
        return await conn.run_sync(_collect)


@pytest.mark.integration
async def test_alembic_round_trip_slice613_digest_and_email_log(engine):
    backend_dir = Path(__file__).resolve().parent.parent
    env = {
        **os.environ,
        "DATABASE_URL": engine.url.render_as_string(hide_password=False),
    }

    def _alembic(*args: str) -> None:
        result = subprocess.run(
            ["alembic", *args],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"alembic {' '.join(args)} failed:\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )

    try:
        _alembic("stamp", "head")
        assert await _table_exists(engine, "email_log"), (
            "email_log missing post-stamp at head"
        )
        assert await _column_exists(
            engine, "email_preferences", "daily_digest_opt_out"
        ), "daily_digest_opt_out missing post-stamp at head"

        _alembic("downgrade", "-1")
        assert not await _table_exists(engine, "email_log"), (
            "email_log should be dropped after downgrade -1"
        )
        assert not await _column_exists(
            engine, "email_preferences", "daily_digest_opt_out"
        ), "daily_digest_opt_out should be dropped after downgrade -1"

        _alembic("upgrade", "head")
        assert await _table_exists(engine, "email_log"), (
            "email_log missing post-upgrade head"
        )
        assert await _column_exists(
            engine, "email_preferences", "daily_digest_opt_out"
        ), "daily_digest_opt_out missing post-upgrade head"
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
