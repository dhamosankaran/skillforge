"""Alembic round-trip — E-043 jd columns + tracker_application_scores.

Spec: docs/specs/phase-5/63-ats-rescan-loop.md §7 + AC-12 + AC-15.

Stamps the test DB to head (ensures the new migration is in the chain),
downgrades one revision (drops the new table + jd columns), then
upgrades back. Mirrors the `tests/test_ingestion_jobs_migration.py`
precedent — runs alembic via subprocess so pytest-asyncio doesn't
conflict with env.py's `asyncio.run(...)`.

Marker-gated as integration; the canonical AC-12 + AC-15 check is the
shell round-trip documented in `db-migration.md`.
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
async def test_alembic_round_trip_e043_jd_columns_and_scores_table(engine):
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
        # Stamp at head — both the new table and the jd columns present.
        _alembic("stamp", "head")
        assert await _table_exists(engine, "tracker_application_scores"), (
            "tracker_application_scores missing post-stamp at head"
        )
        # AC-15 — D-020 closure column-presence assertion.
        assert await _column_exists(
            engine, "tracker_applications_v2", "jd_text"
        ), "jd_text missing post-stamp at head"
        assert await _column_exists(
            engine, "tracker_applications_v2", "jd_hash"
        ), "jd_hash missing post-stamp at head"

        # Downgrade one revision — table + both columns dropped.
        _alembic("downgrade", "-1")
        assert not await _table_exists(engine, "tracker_application_scores"), (
            "tracker_application_scores should be dropped after downgrade -1"
        )
        assert not await _column_exists(
            engine, "tracker_applications_v2", "jd_text"
        ), "jd_text should be dropped after downgrade -1"
        assert not await _column_exists(
            engine, "tracker_applications_v2", "jd_hash"
        ), "jd_hash should be dropped after downgrade -1"

        # Upgrade back to head — table + columns re-created cleanly.
        _alembic("upgrade", "head")
        assert await _table_exists(engine, "tracker_application_scores"), (
            "tracker_application_scores missing post-upgrade head"
        )
        assert await _column_exists(
            engine, "tracker_applications_v2", "jd_text"
        ), "jd_text missing post-upgrade head"
        assert await _column_exists(
            engine, "tracker_applications_v2", "jd_hash"
        ), "jd_hash missing post-upgrade head"
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
