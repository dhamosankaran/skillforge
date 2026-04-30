"""Async ingestion orchestrator (Phase 6 slice 6.10b — B-083b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §6.1 + §4.2 + §12
D-5 / D-6 / D-9 / D-11 / D-13.

Public surface:
    - `enqueue_ingestion(payload, db, *, admin)` — validate / dedupe /
      upload source to R2 / INSERT job row / enqueue RQ job.
    - `get_ingestion_job(job_id, db)` — admin status fetch.
    - `list_recent_ingestion_jobs(db, *, admin_id=None, limit=50)` — admin
      list with optional `mine_only` scope.

The RQ worker (`app/jobs/ingestion_worker.py`) consumes the job row this
service writes; the two are decoupled by the row's `id` so the worker can
restart independently of the request that enqueued it.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from redis import Redis
from rq import Queue
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.core.config import Settings, get_settings
from app.models.ingestion_job import IngestionJob
from app.models.user import User
from app.schemas.ingestion import (
    IngestionArtifacts,
    IngestionJobCreateRequest,
    IngestionJobResponse,
)
from app.services.ingestion_errors import (
    IngestionJobNotFoundError,
    IngestionPayloadError,
    R2UploadError,
)
from app.services.object_storage_service import (
    ObjectStorageError,
    ObjectStorageService,
    get_storage,
)

logger = logging.getLogger(__name__)

# ── Module constants per §12 D-6 ────────────────────────────────────────────
INGESTION_JOB_TIMEOUT_SECONDS = 600
INGESTION_MAX_ATTEMPTS = 3
INGESTION_BACKOFF_SCHEDULE: list[int] = [5, 15, 45]

# Active-job statuses — dedupe lookup considers only these per §4.4 rule 3.
_ACTIVE_STATUSES = (
    "pending",
    "running",
    "generating",
    "critiquing",
    "publishing",
)

# Dedupe lookup window — re-issuing the same source after a job has fully
# settled (>retention window) creates a fresh job rather than returning the
# old one. Matches "active job window" framing in spec §4.4 rule 3.
_DEDUPE_RETENTION_WINDOW = timedelta(days=7)


# ── R2 key scheme per spec §6.4 ─────────────────────────────────────────────
def _source_r2_key(job_id: str) -> str:
    return f"ingestion/{job_id}/source.md"


def draft_r2_key(job_id: str) -> str:
    return f"ingestion/{job_id}/draft.json"


def critique_r2_key(job_id: str) -> str:
    return f"ingestion/{job_id}/critique.json"


# ── RQ queue ────────────────────────────────────────────────────────────────
_redis_singleton: Optional[Redis] = None


def get_redis(settings: Optional[Settings] = None) -> Redis:
    """Return a process-cached Redis client bound to `settings.redis_url`."""
    global _redis_singleton
    if _redis_singleton is None:
        s = settings or get_settings()
        _redis_singleton = Redis.from_url(s.redis_url)
    return _redis_singleton


def get_queue(settings: Optional[Settings] = None) -> Queue:
    """Return the RQ queue used for ingestion jobs."""
    s = settings or get_settings()
    return Queue(
        s.rq_ingestion_queue,
        connection=get_redis(s),
        default_timeout=s.rq_default_timeout_seconds,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────
def _compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _to_response(job: IngestionJob) -> IngestionJobResponse:
    """Map an ORM `IngestionJob` row to the public response schema."""
    return IngestionJobResponse(
        job_id=job.id,
        status=job.status,
        source_format=job.source_format,
        source_content_sha256=job.source_content_sha256,
        target_deck_slug=job.target_deck_slug,
        target_deck_id=job.target_deck_id,
        generated_lesson_ids=list(job.generated_lesson_ids or []),
        generated_quiz_item_count=job.generated_quiz_item_count,
        critique_verdict=job.critique_verdict,
        error_message=job.error_message,
        current_attempt=job.current_attempt,
        max_attempts=job.max_attempts,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        artifacts=IngestionArtifacts(
            source_r2_key=job.source_r2_key,
            draft_r2_key=job.draft_r2_key,
            critique_r2_key=job.critique_r2_key,
        ),
    )


async def _find_active_dedupe_job(
    db: AsyncSession, source_sha: str
) -> Optional[IngestionJob]:
    """Return the most recent active job with matching source hash.

    Per §12 D-5 idempotency floor: same source within an active-job window
    returns the existing job. Bound by `_DEDUPE_RETENTION_WINDOW` so a long-
    settled hash doesn't shadow a fresh enqueue.
    """
    cutoff = datetime.now(timezone.utc) - _DEDUPE_RETENTION_WINDOW
    stmt = (
        select(IngestionJob)
        .where(
            IngestionJob.source_content_sha256 == source_sha,
            IngestionJob.status.in_(_ACTIVE_STATUSES),
            IngestionJob.created_at >= cutoff,
        )
        .order_by(desc(IngestionJob.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Public surface ──────────────────────────────────────────────────────────
async def enqueue_ingestion(
    payload: IngestionJobCreateRequest,
    db: AsyncSession,
    *,
    admin: User,
    storage: Optional[ObjectStorageService] = None,
    queue: Optional[Queue] = None,
) -> IngestionJobResponse:
    """Validate → dedupe → upload source → INSERT job row → enqueue RQ.

    Returns 202-shaped response with `status='pending'` (or the existing
    job's status on dedupe). Raises:
        - `IngestionPayloadError` (400) — Pydantic-side already covers
          size cap / min length; this layer surfaces post-validation
          domain errors (e.g. unknown deck slug post-MVP).
        - `R2UploadError` (502) — R2 upload failed; no job row created.
    """
    storage = storage or get_storage()
    queue = queue or get_queue()

    source_sha = _compute_sha256(payload.source_text)

    # ── Dedupe per D-5 — same source in active window returns existing job.
    existing = await _find_active_dedupe_job(db, source_sha)
    if existing is not None:
        logger.info(
            "ingestion dedupe hit: job_id=%s source_sha=%s admin_id=%s",
            existing.id, source_sha[:12], admin.id,
        )
        return _to_response(existing)

    # ── Allocate the job_id up-front so the R2 key + DB row line up.
    job_id = str(uuid.uuid4())
    source_key = _source_r2_key(job_id)

    # ── Upload source.md to R2 (sync boto3 wrapped in to_thread per D-11).
    try:
        await asyncio.to_thread(
            storage.put_object,
            source_key,
            payload.source_text.encode("utf-8"),
            "text/markdown",
        )
    except ObjectStorageError as exc:
        # Surface as the route-mappable error class — keeps boto3 behind
        # the service boundary.
        raise R2UploadError(f"R2 source upload failed: {exc}") from exc

    # ── INSERT job row (status='pending').
    job = IngestionJob(
        id=job_id,
        status="pending",
        source_format="markdown",
        source_content_sha256=source_sha,
        source_r2_key=source_key,
        created_by_user_id=admin.id,
        target_deck_slug=payload.target_deck_slug,
        max_attempts=INGESTION_MAX_ATTEMPTS,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    # ── Enqueue the RQ job. Worker entry: `ingestion_worker.run_ingestion`.
    queue.enqueue(
        "app.jobs.ingestion_worker.run_ingestion",
        job_id,
        job_timeout=INGESTION_JOB_TIMEOUT_SECONDS,
        job_id=job_id,
    )

    # ── Telemetry (D-13). All admin events carry `internal: true`.
    analytics_track(
        admin.id,
        "ingestion_job_enqueued",
        {
            "admin_id": admin.id,
            "job_id": job.id,
            "source_content_sha256": source_sha,
            "target_deck_slug": payload.target_deck_slug,
            "source_size_bytes": len(payload.source_text.encode("utf-8")),
            "internal": True,
        },
    )

    return _to_response(job)


async def get_ingestion_job(
    job_id: str, db: AsyncSession
) -> IngestionJobResponse:
    """Return job status. Raises `IngestionJobNotFoundError` on miss."""
    result = await db.execute(
        select(IngestionJob).where(IngestionJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise IngestionJobNotFoundError(job_id)
    return _to_response(job)


async def list_recent_ingestion_jobs(
    db: AsyncSession,
    *,
    admin_id: Optional[str] = None,
    limit: int = 50,
) -> list[IngestionJobResponse]:
    """List recent jobs, newest first. `admin_id` scopes to one admin."""
    stmt = select(IngestionJob).order_by(desc(IngestionJob.created_at)).limit(limit)
    if admin_id is not None:
        stmt = stmt.where(IngestionJob.created_by_user_id == admin_id)
    result = await db.execute(stmt)
    return [_to_response(job) for job in result.scalars().all()]
