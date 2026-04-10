"""Rate limiting tests (Spec #25).

Verifies that slowapi returns 429 when the per-route limit is exceeded.
Auth endpoints are capped at 10 req/min — so 11 rapid requests must trigger
a 429 on the last one.

The global conftest disables the limiter so other tests are not affected.
This file re-enables it for its own scope and cleans up afterward.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import limiter
from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _clear_storage() -> None:
    """Reset in-memory rate-limit counters."""
    if hasattr(limiter, "_storage"):
        storage = limiter._storage
        for attr in ("storage", "expirations", "events"):
            bucket = getattr(storage, attr, None)
            if bucket is not None and hasattr(bucket, "clear"):
                bucket.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def rl_client():
    """HTTP client with rate limiting enabled. Cleans up on teardown."""
    _clear_storage()
    limiter.enabled = True

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    limiter.enabled = False
    _clear_storage()


async def test_rate_limit_returns_429(rl_client):
    """Auth endpoints are limited to 10/min. The 11th request gets 429.

    The requests will fail auth (401) but still count toward the rate
    limit — slowapi counts all requests regardless of response status.
    """
    endpoint = "/api/v1/auth/google"
    payload = {"credential": "invalid-token"}

    # Make 10 requests — all should return non-429 (likely 401).
    for i in range(10):
        resp = await rl_client.post(endpoint, json=payload)
        assert resp.status_code != 429, (
            f"Hit rate limit too early on request {i + 1}"
        )

    # 11th request should be rate-limited.
    resp = await rl_client.post(endpoint, json=payload)
    assert resp.status_code == 429
