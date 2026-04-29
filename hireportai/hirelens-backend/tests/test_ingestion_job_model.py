"""IngestionJob model schema tests (Phase 6 slice 6.10a — B-083a foundation).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §5.3 + §7.

Verifies that the `ingestion_jobs` table matches the spec column /
constraint / index contract. The dedicated alembic round-trip test
lives in `test_phase6_schema.py` (extended by this slice's migration);
this file covers the ORM-side row-shape assertions plus a smoke
INSERT/SELECT to confirm column types are usable.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect

from app.models.ingestion_job import IngestionJob

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _reflect(engine):
    def _collect(conn):
        insp = inspect(conn)
        cols = {c["name"]: c for c in insp.get_columns("ingestion_jobs")}
        idxs = insp.get_indexes("ingestion_jobs")
        fks = insp.get_foreign_keys("ingestion_jobs")
        return cols, idxs, fks

    async with engine.connect() as conn:
        return await conn.run_sync(_collect)


# ---------------------------------------------------------------------------
# §5.3 column contract + index contract
# ---------------------------------------------------------------------------
async def test_ingestion_jobs_table_shape(engine):
    cols, idxs, fks = await _reflect(engine)

    # Required columns per §5.3.
    expected = {
        "id",
        "status",
        "source_format",
        "source_content_sha256",
        "source_r2_key",
        "draft_r2_key",
        "critique_r2_key",
        "created_by_user_id",
        "target_deck_slug",
        "target_deck_id",
        "generated_lesson_ids",
        "generated_quiz_item_count",
        "critique_verdict",
        "error_message",
        "current_attempt",
        "max_attempts",
        "created_at",
        "started_at",
        "completed_at",
    }
    assert expected.issubset(cols.keys()), (
        f"Missing columns: {expected - cols.keys()}"
    )

    # Three locked indexes per §7 + spec §5.3 commentary.
    index_columns = {tuple(ix["column_names"]) for ix in idxs}
    assert ("status", "created_at") in index_columns or ("status",) in index_columns, (
        f"Need a (status, created_at) or (status) index; got {index_columns}"
    )
    assert ("source_content_sha256",) in index_columns, (
        f"Need a source_content_sha256 dedupe index; got {index_columns}"
    )
    assert (
        ("created_by_user_id", "created_at") in index_columns
        or ("created_by_user_id",) in index_columns
    ), (
        f"Need a (created_by_user_id, created_at) index; got {index_columns}"
    )

    # FK shapes per §7.
    fk_targets = {
        (tuple(fk["constrained_columns"]), fk["referred_table"]): fk
        for fk in fks
    }
    assert (("created_by_user_id",), "users") in fk_targets, "Missing FK to users"
    assert (("target_deck_id",), "decks") in fk_targets, "Missing FK to decks"
    # ON DELETE SET NULL on both — admin deletion must not orphan job history.
    for key in (("created_by_user_id",), "users"), (("target_deck_id",), "decks"):
        cc, target = key
        fk = fk_targets[(cc, target)]
        opts = fk.get("options") or {}
        on_delete = opts.get("ondelete") or fk.get("ondelete") or ""
        assert "SET NULL" in on_delete.upper(), (
            f"FK {cc} → {target} should be ON DELETE SET NULL; got {opts}"
        )


# ---------------------------------------------------------------------------
# Smoke INSERT — confirms column types usable + defaults take effect
# ---------------------------------------------------------------------------
async def test_ingestion_job_insert_round_trip(db_session):
    job = IngestionJob(
        id=str(uuid.uuid4()),
        status="pending",
        source_content_sha256="0" * 64,
        source_r2_key="ingestion/job-x/source.md",
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)

    assert job.status == "pending"
    assert job.source_format == "markdown"
    assert job.current_attempt == 0
    assert job.max_attempts == 3
    assert job.generated_lesson_ids == []
    assert job.generated_quiz_item_count == 0
    assert job.created_at is not None
    assert job.started_at is None
    assert job.completed_at is None
