"""Ingestion orchestrator service tests (Phase 6 slice 6.10b — B-083b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §10.1 + §11 AC-3 /
AC-4 / AC-5 / AC-11 / AC-12.

Mocks: `ObjectStorageService.put_object` (R2) + `Queue.enqueue` (RQ).
The slice 6.4b admin services + DB are real.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.models.ingestion_job import IngestionJob
from app.models.user import User
from app.schemas.ingestion import IngestionJobCreateRequest
from app.services import ingestion_service
from app.services.ingestion_errors import (
    IngestionJobNotFoundError,
    R2UploadError,
)
from app.services.object_storage_service import ObjectStorageError

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Shared fixtures ─────────────────────────────────────────────────────────
SAMPLE_SOURCE = (
    "# Sample lesson source\n\n"
    "## Concept\n\n"
    + ("This is sample source markdown content for ingestion testing. " * 10)
    + "\n\n## Production\n\nProduction notes go here.\n"
)


async def _create_admin(db, *, email_suffix: str = "") -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"admin-{uuid.uuid4()}{email_suffix}@ingest-test.com",
        name="Ingest Test Admin",
        role="admin",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _make_storage_mock() -> MagicMock:
    storage = MagicMock()
    storage.put_object = MagicMock(return_value="s3://bucket/key")
    storage.get_object = MagicMock(return_value=b"")
    return storage


def _make_queue_mock() -> MagicMock:
    queue = MagicMock()
    queue.enqueue = MagicMock()
    return queue


# ── AC-3 — happy path ──────────────────────────────────────────────────────
async def test_enqueue_writes_source_to_r2_and_creates_pending_job_row(db_session):
    admin = await _create_admin(db_session)
    storage = _make_storage_mock()
    queue = _make_queue_mock()
    payload = IngestionJobCreateRequest(source_text=SAMPLE_SOURCE)

    response = await ingestion_service.enqueue_ingestion(
        payload, db_session, admin=admin, storage=storage, queue=queue,
    )

    assert response.status == "pending"
    assert response.source_content_sha256 == ingestion_service._compute_sha256(
        SAMPLE_SOURCE
    )
    storage.put_object.assert_called_once()
    args, kwargs = storage.put_object.call_args
    # Key is the deterministic ingestion path scheme.
    assert args[0].startswith("ingestion/") and args[0].endswith("/source.md")
    # Body is the UTF-8 bytes; content type is text/markdown.
    assert args[1] == SAMPLE_SOURCE.encode("utf-8")
    assert args[2] == "text/markdown"

    # Exactly one RQ enqueue call with the worker entry point + the job_id.
    queue.enqueue.assert_called_once()
    enq_args, enq_kwargs = queue.enqueue.call_args
    assert enq_args[0] == "app.jobs.ingestion_worker.run_ingestion"
    assert enq_args[1] == response.job_id
    assert enq_kwargs["job_timeout"] == ingestion_service.INGESTION_JOB_TIMEOUT_SECONDS

    # Row landed with status='pending' + correct admin attribution.
    row = (
        await db_session.execute(
            select(IngestionJob).where(IngestionJob.id == response.job_id)
        )
    ).scalar_one()
    assert row.status == "pending"
    assert row.created_by_user_id == admin.id
    assert row.source_r2_key == args[0]


# ── AC-4 — dedupe within active window ─────────────────────────────────────
async def test_dedupe_returns_existing_job_without_second_r2_or_enqueue(db_session):
    admin = await _create_admin(db_session)
    storage = _make_storage_mock()
    queue = _make_queue_mock()
    payload = IngestionJobCreateRequest(source_text=SAMPLE_SOURCE)

    first = await ingestion_service.enqueue_ingestion(
        payload, db_session, admin=admin, storage=storage, queue=queue,
    )
    second = await ingestion_service.enqueue_ingestion(
        payload, db_session, admin=admin, storage=storage, queue=queue,
    )

    assert second.job_id == first.job_id
    # Storage + RQ were each called exactly once (first call only).
    assert storage.put_object.call_count == 1
    assert queue.enqueue.call_count == 1


async def test_dedupe_does_not_match_terminal_status(db_session):
    """A 'completed' job with the same hash does NOT shadow a fresh enqueue."""
    admin = await _create_admin(db_session)
    storage = _make_storage_mock()
    queue = _make_queue_mock()
    payload = IngestionJobCreateRequest(source_text=SAMPLE_SOURCE)

    first = await ingestion_service.enqueue_ingestion(
        payload, db_session, admin=admin, storage=storage, queue=queue,
    )
    # Mark first job as completed so dedupe should NOT pick it up.
    row = (
        await db_session.execute(
            select(IngestionJob).where(IngestionJob.id == first.job_id)
        )
    ).scalar_one()
    row.status = "completed"
    await db_session.flush()

    second = await ingestion_service.enqueue_ingestion(
        payload, db_session, admin=admin, storage=storage, queue=queue,
    )

    assert second.job_id != first.job_id
    assert storage.put_object.call_count == 2
    assert queue.enqueue.call_count == 2


# ── AC-5 — payload size cap (Pydantic-level validation) ────────────────────
async def test_payload_below_min_length_raises_validation_error():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        IngestionJobCreateRequest(source_text="too short")


async def test_payload_above_max_length_raises_validation_error():
    from pydantic import ValidationError

    huge = "a" * (1_048_576 + 1)
    with pytest.raises(ValidationError):
        IngestionJobCreateRequest(source_text=huge)


# ── R2 upload failure → no job row created ──────────────────────────────────
async def test_r2_upload_failure_raises_r2_upload_error_without_job_row(db_session):
    admin = await _create_admin(db_session)
    storage = _make_storage_mock()
    storage.put_object = MagicMock(
        side_effect=ObjectStorageError("simulated R2 outage")
    )
    queue = _make_queue_mock()
    payload = IngestionJobCreateRequest(source_text=SAMPLE_SOURCE)

    with pytest.raises(R2UploadError):
        await ingestion_service.enqueue_ingestion(
            payload, db_session, admin=admin, storage=storage, queue=queue,
        )

    # No job row landed; no RQ enqueue.
    rows = (
        await db_session.execute(
            select(IngestionJob).where(IngestionJob.created_by_user_id == admin.id)
        )
    ).scalars().all()
    assert rows == []
    assert queue.enqueue.call_count == 0


# ── AC-11 / AC-12 — get_ingestion_job lookup ───────────────────────────────
async def test_get_ingestion_job_returns_job_when_present(db_session):
    admin = await _create_admin(db_session)
    storage = _make_storage_mock()
    queue = _make_queue_mock()
    payload = IngestionJobCreateRequest(source_text=SAMPLE_SOURCE)
    enqueued = await ingestion_service.enqueue_ingestion(
        payload, db_session, admin=admin, storage=storage, queue=queue,
    )

    fetched = await ingestion_service.get_ingestion_job(enqueued.job_id, db_session)
    assert fetched.job_id == enqueued.job_id
    assert fetched.status == "pending"


async def test_get_ingestion_job_raises_not_found_for_unknown_id(db_session):
    with pytest.raises(IngestionJobNotFoundError):
        await ingestion_service.get_ingestion_job(str(uuid.uuid4()), db_session)


# ── list_recent_ingestion_jobs admin scope ─────────────────────────────────
async def test_list_recent_ingestion_jobs_mine_only_filters_to_caller(db_session):
    admin_a = await _create_admin(db_session, email_suffix="-a")
    admin_b = await _create_admin(db_session, email_suffix="-b")
    storage = _make_storage_mock()
    queue = _make_queue_mock()

    # admin_a enqueues two jobs (different sources to bypass dedupe).
    for i in range(2):
        await ingestion_service.enqueue_ingestion(
            IngestionJobCreateRequest(source_text=SAMPLE_SOURCE + f" variant-{i}"),
            db_session, admin=admin_a, storage=storage, queue=queue,
        )
    # admin_b enqueues one job.
    await ingestion_service.enqueue_ingestion(
        IngestionJobCreateRequest(source_text=SAMPLE_SOURCE + " variant-b"),
        db_session, admin=admin_b, storage=storage, queue=queue,
    )

    only_a = await ingestion_service.list_recent_ingestion_jobs(
        db_session, admin_id=admin_a.id
    )
    only_b = await ingestion_service.list_recent_ingestion_jobs(
        db_session, admin_id=admin_b.id
    )

    assert len(only_a) == 2
    assert len(only_b) == 1
    assert all(j.source_content_sha256 for j in only_a)


# Mark async-mock import as used so import-pruning agents leave it alone.
_ = AsyncMock
