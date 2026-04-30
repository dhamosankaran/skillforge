"""Admin ingest route tests (Phase 6 slice 6.10b — B-083b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §10.3 + §11
AC-1..AC-6 / AC-11 / AC-12 / AC-16 / AC-17.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update as sql_update

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.main import app
from app.models.admin_audit_log import AdminAuditLog
from app.models.ingestion_job import IngestionJob
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


SAMPLE_SOURCE = (
    "# Source\n\n"
    + ("This is a long enough sample source body for the ingestion endpoint. " * 5)
    + "\n"
)


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


@pytest_asyncio.fixture(loop_scope="session")
async def patched_storage_and_queue():
    """Auto-patch the orchestrator's R2 + RQ deps for every route test."""
    storage = MagicMock()
    storage.put_object = MagicMock(return_value="s3://bucket/key")
    queue = MagicMock()
    queue.enqueue = MagicMock()
    with (
        patch("app.services.ingestion_service.get_storage", return_value=storage),
        patch("app.services.ingestion_service.get_queue", return_value=queue),
    ):
        yield storage, queue


async def _sign_in_admin(client, db_session, *, suffix: str = "") -> tuple[str, str]:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}{suffix}@admin-ingest-test.com",
        "name": "Admin Ingest Tester",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200
    data = resp.json()
    user_id = data["user"]["id"]
    await db_session.execute(
        sql_update(User).where(User.id == user_id).values(role="admin")
    )
    await db_session.flush()
    return data["access_token"], user_id


async def _sign_in_user(client, db_session) -> str:
    info = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@user-ingest-test.com",
        "name": "Plain User",
        "avatar_url": None,
    }
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=info),
    ):
        resp = await client.post("/api/v1/auth/google", json={"credential": "tok"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── AC-1 — unauthed POST → 401 ─────────────────────────────────────────────
async def test_post_unauthed_returns_401(client, patched_storage_and_queue):
    resp = await client.post(
        "/api/v1/admin/ingest", json={"source_text": SAMPLE_SOURCE}
    )
    assert resp.status_code == 401


# ── AC-2 + AC-16 — non-admin → 403 ─────────────────────────────────────────
async def test_post_non_admin_returns_403(client, db_session, patched_storage_and_queue):
    token = await _sign_in_user(client, db_session)
    resp = await client.post(
        "/api/v1/admin/ingest",
        json={"source_text": SAMPLE_SOURCE},
        headers=_auth(token),
    )
    assert resp.status_code == 403


# ── AC-3 — admin happy path → 202 + IngestionJobResponse ───────────────────
async def test_post_admin_happy_path_returns_202(
    client, db_session, patched_storage_and_queue
):
    storage, queue = patched_storage_and_queue
    token, _ = await _sign_in_admin(client, db_session)

    resp = await client.post(
        "/api/v1/admin/ingest",
        json={
            "source_text": SAMPLE_SOURCE,
            "target_deck_slug": "ingest-test-deck",
            "expected_lesson_count": 1,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["target_deck_slug"] == "ingest-test-deck"

    # Single R2 upload + single RQ enqueue.
    assert storage.put_object.call_count == 1
    assert queue.enqueue.call_count == 1


# ── AC-5 — payload too small → 422 (Pydantic validation) ───────────────────
async def test_post_short_source_returns_422(
    client, db_session, patched_storage_and_queue
):
    token, _ = await _sign_in_admin(client, db_session)
    resp = await client.post(
        "/api/v1/admin/ingest",
        json={"source_text": "tiny"},
        headers=_auth(token),
    )
    # Pydantic field validation surfaces as 422 by FastAPI default.
    assert resp.status_code == 422


# ── AC-6 — per-admin 10/hour cap ───────────────────────────────────────────
async def test_post_eleventh_call_returns_429_for_same_admin(
    client, db_session, patched_storage_and_queue
):
    token, _ = await _sign_in_admin(client, db_session)

    # Conftest disables the limiter globally; re-enable for this test only.
    limiter.enabled = True
    try:
        # Use unique source_text per call to bypass dedupe and force 10
        # distinct enqueues — the 11th must trip the slowapi 10/hour cap.
        for i in range(10):
            resp = await client.post(
                "/api/v1/admin/ingest",
                json={"source_text": SAMPLE_SOURCE + f" salt-{i}"},
                headers=_auth(token),
            )
            assert resp.status_code == 202, f"call {i}: {resp.status_code} {resp.text}"
        eleventh = await client.post(
            "/api/v1/admin/ingest",
            json={"source_text": SAMPLE_SOURCE + " salt-overflow"},
            headers=_auth(token),
        )
        assert eleventh.status_code == 429
    finally:
        limiter.enabled = False
        # Reset slowapi's in-memory counter store so other tests aren't
        # affected by accumulated counters.
        limiter.reset()


# ── AC-11 / AC-12 — GET status path ────────────────────────────────────────
async def test_get_known_job_returns_200(client, db_session, patched_storage_and_queue):
    token, _ = await _sign_in_admin(client, db_session)
    enqueue_resp = await client.post(
        "/api/v1/admin/ingest",
        json={"source_text": SAMPLE_SOURCE},
        headers=_auth(token),
    )
    job_id = enqueue_resp.json()["job_id"]

    get_resp = await client.get(
        f"/api/v1/admin/ingest/{job_id}", headers=_auth(token)
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["job_id"] == job_id


async def test_get_unknown_job_returns_404(
    client, db_session, patched_storage_and_queue
):
    token, _ = await _sign_in_admin(client, db_session)
    bogus = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/admin/ingest/{bogus}", headers=_auth(token))
    assert resp.status_code == 404


# ── GET list ───────────────────────────────────────────────────────────────
async def test_get_list_recent_jobs_returns_caller_only_when_mine_only(
    client, db_session, patched_storage_and_queue
):
    token_a, _ = await _sign_in_admin(client, db_session, suffix="-list-a")
    token_b, admin_b_id = await _sign_in_admin(client, db_session, suffix="-list-b")

    # admin_b enqueues 1 job.
    await client.post(
        "/api/v1/admin/ingest",
        json={"source_text": SAMPLE_SOURCE + " admin-b"},
        headers=_auth(token_b),
    )

    # admin_a calls list with mine_only=true → empty.
    resp_a = await client.get(
        "/api/v1/admin/ingest?mine_only=true&limit=10", headers=_auth(token_a)
    )
    assert resp_a.status_code == 200
    job_ids_a = [j["job_id"] for j in resp_a.json()]
    # admin_b's job must NOT appear in admin_a's mine_only list.
    rows = (
        await db_session.execute(
            select(IngestionJob).where(IngestionJob.created_by_user_id == admin_b_id)
        )
    ).scalars().all()
    for job in rows:
        assert job.id not in job_ids_a

    # admin_b mine_only=true → at least the freshly enqueued job.
    resp_b = await client.get(
        "/api/v1/admin/ingest?mine_only=true&limit=10", headers=_auth(token_b)
    )
    assert resp_b.status_code == 200
    assert any(j["job_id"] == rows[0].id for j in resp_b.json())


# ── AC-17 — one admin_audit_log row per POST ───────────────────────────────
async def test_post_writes_one_admin_audit_log_row(
    client, db_session, patched_storage_and_queue
):
    token, admin_id = await _sign_in_admin(client, db_session)
    resp = await client.post(
        "/api/v1/admin/ingest",
        json={"source_text": SAMPLE_SOURCE + " audit"},
        headers=_auth(token),
    )
    assert resp.status_code == 202

    # `audit_admin_request` schedules a BackgroundTask; FastAPI runs it
    # post-response within the same TestClient transaction. Look it up.
    rows = (
        await db_session.execute(
            select(AdminAuditLog).where(
                AdminAuditLog.admin_id == admin_id,
                AdminAuditLog.route == "/api/v1/admin/ingest",
                AdminAuditLog.method == "POST",
            )
        )
    ).scalars().all()
    assert len(rows) == 1


# ── AC-4 — dedupe at the route boundary returns same job_id ────────────────
async def test_post_dedupe_returns_same_job_id(
    client, db_session, patched_storage_and_queue
):
    token, _ = await _sign_in_admin(client, db_session)
    body = {"source_text": SAMPLE_SOURCE + " dedupe"}

    first = await client.post("/api/v1/admin/ingest", json=body, headers=_auth(token))
    second = await client.post("/api/v1/admin/ingest", json=body, headers=_auth(token))

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
