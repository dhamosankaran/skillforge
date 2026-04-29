"""Object-storage service unit tests (Phase 6 slice 6.10a — B-083a foundation).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §6.4 + §10.5 + D-11.

The service wraps a sync `boto3` client targeting Cloudflare R2 via the
S3-compatible `endpoint_url`. Async surfaces in the FastAPI request path
(B-083b's `enqueue_ingestion`) call into the sync client via
`asyncio.to_thread`; the RQ worker (B-083b) calls it directly. Mocks
patch `boto3.client` at the module boundary — no `moto` introduced this
slice (greenfield mock pattern per Step 1.3 audit).

Lazy-init is load-bearing: production config is absent in test env, so
constructing the client at import time would crash unrelated tests. The
service exposes a `get_storage()` factory that builds the client on first
use only.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.object_storage_service import (
    ObjectStorageError,
    ObjectStorageService,
    get_storage,
)


def _make_settings(**overrides):
    """Return a `Settings`-shaped object with R2 fields populated."""
    base = {
        "r2_account_id": "acct123",
        "r2_access_key_id": "AKID",
        "r2_secret_access_key": "secret",
        "r2_bucket_name": "ingest-test",
        "r2_endpoint_url": "https://acct123.r2.cloudflarestorage.com",
    }
    base.update(overrides)
    settings = MagicMock()
    for key, value in base.items():
        setattr(settings, key, value)
    return settings


def test_put_and_get_round_trip():
    """`put_object` then `get_object` round-trips bytes via the mocked client."""
    settings = _make_settings()
    fake_client = MagicMock()
    fake_client.put_object.return_value = {"ETag": '"abc"'}
    fake_client.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b"hello world"))
    }

    with patch("app.services.object_storage_service.boto3.client", return_value=fake_client) as boto_client:
        svc = ObjectStorageService(settings)
        uri = svc.put_object("ingestion/job-1/source.md", b"hello world", "text/markdown")
        body = svc.get_object("ingestion/job-1/source.md")

    # Single boto3.client call — proves lazy-init is wired (one client per
    # service instance, not per-call).
    assert boto_client.call_count == 1
    assert boto_client.call_args.kwargs["endpoint_url"] == "https://acct123.r2.cloudflarestorage.com"
    fake_client.put_object.assert_called_once_with(
        Bucket="ingest-test",
        Key="ingestion/job-1/source.md",
        Body=b"hello world",
        ContentType="text/markdown",
    )
    assert uri == "s3://ingest-test/ingestion/job-1/source.md"
    assert body == b"hello world"


def test_lazy_init_does_not_construct_client_until_first_use():
    """Constructor must NOT call `boto3.client` — that lands on first put/get."""
    settings = _make_settings()
    with patch("app.services.object_storage_service.boto3.client") as boto_client:
        svc = ObjectStorageService(settings)
        # Construction alone should not have hit boto3.
        assert boto_client.call_count == 0
        # A no-op attribute access also does not hit boto3 (only the
        # explicit `_client` property / first put/get does).
        assert svc.bucket_name == "ingest-test"
        assert boto_client.call_count == 0


def test_put_object_wraps_boto_error_in_object_storage_error():
    """A boto3-side `ClientError` is wrapped so callers depend on our class."""
    from botocore.exceptions import ClientError

    settings = _make_settings()
    fake_client = MagicMock()
    fake_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "nope"}},
        "PutObject",
    )

    with patch("app.services.object_storage_service.boto3.client", return_value=fake_client):
        svc = ObjectStorageService(settings)
        with pytest.raises(ObjectStorageError) as exc:
            svc.put_object("ingestion/job-2/source.md", b"x", "text/markdown")

    assert "AccessDenied" in str(exc.value) or "PutObject" in str(exc.value)


def test_get_storage_factory_uses_settings_singleton():
    """`get_storage()` returns a service bound to `get_settings()` output."""
    settings = _make_settings(r2_bucket_name="another-bucket")
    with patch("app.services.object_storage_service.get_settings", return_value=settings):
        svc = get_storage()
        assert isinstance(svc, ObjectStorageService)
        assert svc.bucket_name == "another-bucket"
