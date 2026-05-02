"""Alembic round-trip — slice 6.13.5a card_quality_signals table (B-094a).

Spec: docs/specs/phase-6/12-quality-signals.md §10.3 + AC-1 + AC-2 +
AC-4.

Stamps the test DB to head (asserts the new table is present),
downgrades one revision (drops it), then upgrades back. Mirrors the
``tests/test_phase6_slice613_migration.py`` precedent — runs alembic
via subprocess so pytest-asyncio doesn't conflict with env.py's
``asyncio.run(...)``.

Marker-gated as integration; the canonical AC-2 check is the shell
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


async def _index_exists(engine, table: str, index_name: str) -> bool:
    def _collect(conn):
        return index_name in {
            ix["name"] for ix in inspect(conn).get_indexes(table)
        }

    async with engine.connect() as conn:
        return await conn.run_sync(_collect)


@pytest.mark.integration
async def test_alembic_round_trip_card_quality_signals(engine):
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
        assert await _table_exists(engine, "card_quality_signals"), (
            "card_quality_signals missing post-stamp at head"
        )
        assert await _index_exists(
            engine,
            "card_quality_signals",
            "ix_card_quality_signals_lesson_source",
        )
        assert await _index_exists(
            engine,
            "card_quality_signals",
            "ix_card_quality_signals_quiz_item_source",
        )
        assert await _index_exists(
            engine,
            "card_quality_signals",
            "ix_card_quality_signals_user",
        )

        _alembic("downgrade", "-1")
        assert not await _table_exists(engine, "card_quality_signals"), (
            "card_quality_signals should be dropped after downgrade -1"
        )

        _alembic("upgrade", "head")
        assert await _table_exists(engine, "card_quality_signals"), (
            "card_quality_signals missing post-upgrade head"
        )
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
