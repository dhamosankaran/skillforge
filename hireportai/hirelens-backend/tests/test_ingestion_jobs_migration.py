"""Alembic round-trip — `ingestion_jobs` migration (Phase 6 slice 6.10a).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §11 AC-18.

Stamps the test DB to the current head, downgrades one revision (drops
`ingestion_jobs`), then upgrades back. Mirrors the
`tests/test_phase6_schema.py::test_alembic_round_trip` precedent — runs
alembic via subprocess so pytest-asyncio doesn't conflict with env.py's
`asyncio.run(...)`.

Marker-gated as integration; the canonical AC-18 check is the shell
round-trip documented in `db-migration.md`.
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


@pytest.mark.integration
async def test_alembic_round_trip_ingestion_jobs(engine):
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
        # Stamp at head — table should be present.
        _alembic("stamp", "head")
        assert await _table_exists(engine, "ingestion_jobs"), (
            "ingestion_jobs missing post-stamp at head"
        )
        # Downgrade one revision — table dropped.
        _alembic("downgrade", "-1")
        assert not await _table_exists(engine, "ingestion_jobs"), (
            "ingestion_jobs should be dropped after downgrade -1"
        )
        # Upgrade back to head — table re-created cleanly.
        _alembic("upgrade", "head")
        assert await _table_exists(engine, "ingestion_jobs"), (
            "ingestion_jobs missing post-upgrade head"
        )
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
