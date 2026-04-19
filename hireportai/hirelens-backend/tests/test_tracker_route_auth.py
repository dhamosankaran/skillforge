"""Route-level auth contract for the tracker surface (spec #45).

Covers two invariants:

1. The legacy unauthenticated ``/api/tracker`` surface no longer exists
   (deleted in P5-S21). Hitting any verb returns 404.
2. The ``/api/v1/tracker`` surface requires a valid bearer token. Hitting
   any verb without one returns 401.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


_LEGACY_CASES = [
    ("GET", "/api/tracker"),
    ("POST", "/api/tracker"),
    ("PATCH", "/api/tracker/some-id"),
    ("DELETE", "/api/tracker/some-id"),
]


@pytest.mark.parametrize("method,path", _LEGACY_CASES)
async def test_legacy_tracker_route_returns_404(client, method: str, path: str):
    resp = await client.request(method, path, json={})
    assert resp.status_code == 404, (
        f"{method} {path} should be deleted but returned {resp.status_code}: "
        f"{resp.text}"
    )


_V1_CASES = [
    ("GET", "/api/v1/tracker"),
    ("POST", "/api/v1/tracker"),
    ("PATCH", "/api/v1/tracker/some-id"),
    ("DELETE", "/api/v1/tracker/some-id"),
]


@pytest.mark.parametrize("method,path", _V1_CASES)
async def test_v1_tracker_requires_auth(client, method: str, path: str):
    resp = await client.request(method, path, json={})
    assert resp.status_code == 401, (
        f"{method} {path} should require auth but returned {resp.status_code}: "
        f"{resp.text}"
    )
