"""Domain exceptions for the AI ingestion pipeline (Phase 6 slice 6.10b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §6.3 + §10.3.

Each class maps to a single HTTP status code at the route boundary
(`app/api/v1/routes/admin_ingest.py`); per `backend.md` §2.4 routes own
the error → HTTP mapping, services raise domain exceptions.
"""
from __future__ import annotations


class IngestionPayloadError(Exception):
    """Request body failed validation (size cap, frontmatter parse, …) → 400."""


class IngestionRateLimitedError(Exception):
    """Per-admin enqueue cap exceeded (per spec §12 D-8) → 429."""


class R2UploadError(Exception):
    """`object_storage_service.put_object` failed at enqueue time → 502.

    Distinct from `ObjectStorageError` (the boto3 wrapper) so the route
    handler can surface a stable HTTP code without touching the boto3 dep.
    """


class IngestionJobNotFoundError(Exception):
    """`get_ingestion_job` lookup miss → 404."""
