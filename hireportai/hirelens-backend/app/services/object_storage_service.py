"""Cloudflare R2 object storage wrapper (Phase 6 slice 6.10a — B-083a).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §6.4 + D-11.

Wraps a sync `boto3` client targeting Cloudflare R2 via the
S3-compatible `endpoint_url` (Cloudflare convention:
`https://<account_id>.r2.cloudflarestorage.com`). Per D-11 the FastAPI
async surfaces (B-083b's `enqueue_ingestion`) call into the sync API via
`asyncio.to_thread`; the RQ worker runs sync natively.

Lazy-init: the `boto3.client` constructor is invoked on first use only.
Production config is absent in test env, so eager construction would
crash unrelated test sessions.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client  # type: ignore

logger = logging.getLogger(__name__)


class ObjectStorageError(Exception):
    """Raised when R2 / S3 client returns an error.

    Wraps `botocore.exceptions.ClientError` / `BotoCoreError` so callers
    depend on this module's class — keeps the boto3 dep behind the
    service boundary.
    """


class ObjectStorageService:
    """Sync R2 client wrapper. One instance per `Settings` object."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self.bucket_name = settings.r2_bucket_name
        self._cached_client: Optional["S3Client"] = None

    @property
    def _client(self) -> "S3Client":
        """Lazy-init the underlying boto3 client.

        Production config is required at first use only — tests that
        never call `put_object` / `get_object` don't need R2 env vars.
        """
        if self._cached_client is None:
            self._cached_client = boto3.client(
                "s3",
                endpoint_url=self._settings.r2_endpoint_url,
                aws_access_key_id=self._settings.r2_access_key_id,
                aws_secret_access_key=self._settings.r2_secret_access_key,
                region_name="auto",  # Cloudflare R2 ignores region but boto3 wants one.
            )
        return self._cached_client

    def put_object(self, key: str, body: bytes, content_type: str) -> str:
        """Upload bytes to R2; returns the `s3://<bucket>/<key>` URI."""
        try:
            self._client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType=content_type,
            )
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError(f"R2 put_object failed for {key}: {exc}") from exc
        return f"s3://{self.bucket_name}/{key}"

    def get_object(self, key: str) -> bytes:
        """Fetch bytes from R2; raises `ObjectStorageError` on any client error."""
        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError(f"R2 get_object failed for {key}: {exc}") from exc
        return response["Body"].read()


def get_storage() -> ObjectStorageService:
    """Construct an `ObjectStorageService` from the cached `Settings`.

    Lazy enough for B-083b's `enqueue_ingestion` to call directly (one
    fresh instance per request is fine — boto3 clients are cheap once
    the underlying TLS pool is warmed). Promote to a singleton if perf
    profiling later flags client construction as hot.
    """
    return ObjectStorageService(get_settings())
